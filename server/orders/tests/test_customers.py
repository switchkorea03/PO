from concurrent.futures import ThreadPoolExecutor
from django.test import TestCase,TransactionTestCase
from django.db import connections
from django.contrib.auth import get_user_model
from orders.models import Customer

class CustomerTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('customer-manager')
        self.client.force_login(self.user)

    def test_repeated_add_returns_same_customer_and_preserves_defaults(self):
        ids=[]
        for i in range(5):
            response=self.client.post('/customers/',{'name':' 범진전자 ','default_type':'domestic','currency':'KRW' if i==0 else 'USD'},content_type='application/json')
            self.assertEqual(response.status_code,200);ids.append(response.json()['id'])
        self.assertEqual(len(set(ids)),1)
        self.assertEqual(Customer.objects.filter(name='범진전자').count(),1)
        self.assertEqual(Customer.objects.get(name='범진전자').currency,'KRW')

class ConcurrentCustomerTests(TransactionTestCase):
    def test_simultaneous_add_creates_one_customer(self):
        from django.test import Client
        user=get_user_model().objects.create_user('customer-manager')
        def add(_):
            try:
                client=Client();client.force_login(user)
                response=client.post('/customers/',{'name':'범진전자'},content_type='application/json')
                return response.status_code,response.json()['id']
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(add,range(3)))
        self.assertTrue(all(status==200 for status,_ in results))
        self.assertEqual(len({key for _,key in results}),1)
        self.assertEqual(Customer.objects.filter(name='범진전자').count(),1)

class CustomerMergeMigrationTests(TransactionTestCase):
    def test_duplicate_merge_keeps_all_po_records(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor=MigrationExecutor(connection)
        current=executor.loader.graph.leaf_nodes('orders')
        previous=[('orders','0002_changeevent_consumed_at')]
        latest=[('orders','0003_unique_customer_name')]
        executor.migrate(previous)
        try:
            apps=executor.loader.project_state(previous).apps
            OldCustomer=apps.get_model('orders','Customer');OldOrder=apps.get_model('orders','Order')
            a=OldCustomer.objects.create(name='중복고객');b=OldCustomer.objects.create(name='중복고객')
            first=OldOrder.objects.create(customer=a,po_number='PO-1',order_type='domestic')
            second=OldOrder.objects.create(customer=b,po_number='PO-2',order_type='domestic')
            executor=MigrationExecutor(connection);executor.migrate(latest)
            self.assertEqual(Customer.objects.filter(name='중복고객').count(),1)
            MergedOrder=executor.loader.project_state(latest).apps.get_model('orders','Order')
            self.assertEqual(MergedOrder.objects.filter(id__in=[first.id,second.id]).count(),2)
            self.assertEqual(MergedOrder.objects.get(pk=first.id).customer_id,MergedOrder.objects.get(pk=second.id).customer_id)
        finally:MigrationExecutor(connection).migrate(current)

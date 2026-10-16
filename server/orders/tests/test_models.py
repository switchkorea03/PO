from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from orders.models import Customer, Order, OrderLine
from work.models import Task

class ModelTests(TestCase):
    def setUp(self):
        self.customer=Customer.objects.create(name="범진전자")
        self.order=Order.objects.create(customer=self.customer,po_number="P-100",order_type="domestic")
    def test_money_precision(self):
        line=OrderLine.objects.create(order=self.order,code="A",name="부품",quantity=Decimal("0.1"),unit="EA",unit_price=Decimal("0.2"),currency="KRW")
        line.refresh_from_db()
        self.assertEqual(line.amount,Decimal("0.02"))
    def test_nonpositive_quantity_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderLine.objects.create(order=self.order,code="A",name="부품",quantity=0,unit="EA")
    def test_duplicate_work_scope_rejected(self):
        Task.objects.create(order=self.order,scope_key=f"order:{self.order.id}",kind="overseas_invoice",title="인보이스+ERP")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Task.objects.create(order=self.order,scope_key=f"order:{self.order.id}",kind="overseas_invoice",title="인보이스+ERP")

from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.models import Shipment,ShipmentLine
from orders.services import confirm_shipment
from work.services import reconcile_order
from .factories import make_order


class InlineDueTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('due-manager')
        self.client.force_login(self.user)

    def planned_order(self,kind='domestic'):
        order=make_order(kind,quantities=('100','200'),dues=('2026-11-17',))
        shipment=Shipment.objects.create(order=order,sequence=1,
            ship_on=date(2026,11,17) if kind=='domestic' else None,
            etd=date(2026,11,17) if kind=='overseas' else None)
        ShipmentLine.objects.bulk_create([ShipmentLine(shipment=shipment,line=line,quantity=line.quantity) for line in order.lines.all()])
        reconcile_order(order.id,self.user.id)
        return order,shipment

    def test_list_save_moves_only_edited_items_pending_schedule(self):
        order,shipment=self.planned_order();line,other=list(order.lines.all())
        response=self.client.post(f'/lines/{line.id}/due/',{'requested_due':'2026-11-20',
            'row_version':order.row_version,'return_to':'/orders/?type=domestic'},follow=True)
        self.assertRedirects(response,'/orders/?type=domestic')
        self.assertContains(response,'납기일을 저장했습니다.')
        line.refresh_from_db();other.refresh_from_db()
        self.assertEqual(line.requested_due,date(2026,11,20));self.assertEqual(other.requested_due,date(2026,11,17))
        self.assertEqual(shipment.allocations.get().line_id,other.id)
        moved=order.shipments.exclude(pk=shipment.id).get()
        self.assertEqual(moved.ship_on,date(2026,11,20))
        self.assertEqual(moved.allocations.get().line_id,line.id)
        self.assertEqual(order.tasks.get(shipment=moved,kind='domestic_request').effective_on,date(2026,11,19))
        self.assertTrue(order.history.filter(action='update_requested_due',target=str(line.id)).exists())

    def test_stale_or_invalid_due_does_not_mutate_data(self):
        order,shipment=self.planned_order();line=order.lines.first()
        self.assertEqual(self.client.post(f'/lines/{line.id}/due/',{'requested_due':'2026-11-20','row_version':999},content_type='application/json').status_code,409)
        self.assertEqual(self.client.post(f'/lines/{line.id}/due/',{'requested_due':'','row_version':order.row_version},content_type='application/json').status_code,422)
        line.refresh_from_db();self.assertEqual(line.requested_due,date(2026,11,17))
        self.assertEqual(order.shipments.count(),1)

    def test_completed_actuals_are_not_moved(self):
        order,shipment=self.planned_order();confirm_shipment(shipment.id,self.user.id,shipment.row_version)
        order.refresh_from_db();line=order.lines.first()
        response=self.client.post(f'/lines/{line.id}/due/',{'requested_due':'2026-11-20','row_version':order.row_version},content_type='application/json')
        self.assertEqual(response.status_code,200)
        shipment.refresh_from_db();self.assertEqual(shipment.ship_on,date(2026,11,17));self.assertTrue(shipment.completed)
        self.assertEqual(order.shipments.count(),1)

    def test_overseas_due_does_not_change_etd_based_work(self):
        order,shipment=self.planned_order('overseas');line=order.lines.first()
        before=order.tasks.get(shipment=shipment,kind='overseas_erp').effective_on
        response=self.client.post(f'/lines/{line.id}/due/',{'requested_due':'2026-11-20','row_version':order.row_version},content_type='application/json')
        self.assertEqual(response.status_code,200)
        shipment.refresh_from_db();self.assertEqual(shipment.etd,date(2026,11,17))
        self.assertEqual(order.tasks.get(shipment=shipment,kind='overseas_erp').effective_on,before)

    def test_list_contains_inline_date_controls(self):
        order,shipment=self.planned_order()
        response=self.client.get('/orders/')
        for line in order.lines.all():self.assertContains(response,f'action="/lines/{line.id}/due/"')

    def test_editing_all_due_dates_updates_pending_calendar_plans(self):
        order,shipment=self.planned_order()
        response=self.client.get(f'/orders/{order.id}/edit/')
        data=response.context['initial_data']
        for line in data['lines']:line['requested_due']='2026-11-20'
        saved=self.client.post(f'/orders/{order.id}/edit/',data,content_type='application/json')
        self.assertEqual(saved.status_code,200)
        self.assertEqual(set(order.lines.values_list('requested_due',flat=True)),{date(2026,11,20)})
        self.assertEqual(set(order.shipments.filter(cancelled=False,completed=False).values_list('ship_on',flat=True)),{date(2026,11,20)})

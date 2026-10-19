from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from common.contracts import ShipmentInput
from orders.tests.factories import make_order,make_shipment
from orders.services import save_shipment
from work.models import Task
from work.services import reconcile_order,move_task,set_substep,review_completed_task
class ReconcileTests(TestCase):
    def setUp(self):self.user=get_user_model().objects.create_user("manager")
    def test_stable_ids_and_manual_dates_survive(self):
        order=make_order();shipment=make_shipment(order,"100",ship_on="2026-10-19")
        reconcile_order(order.id,self.user.id);ids=set(order.tasks.values_list("id",flat=True))
        reconcile_order(order.id,self.user.id);self.assertEqual(set(order.tasks.values_list("id",flat=True)),ids)
        task=order.tasks.get(kind="domestic_share")
        move_task(task.id,date(2026,10,15),self.user.id,task.row_version)
        save_shipment(order.id,ShipmentInput(shipment.id,date(2026,10,20),None,None,{order.lines.first().id:Decimal(100)}),self.user.id,shipment.row_version)
        task.refresh_from_db();self.assertEqual(task.effective_on,date(2026,10,15));self.assertTrue(task.recalc_needed)
        move_task(task.id,None,self.user.id,task.row_version);task.refresh_from_db();self.assertEqual(task.effective_on,date(2026,10,19))
    def test_completed_date_is_preserved_but_flagged(self):
        order=make_order();shipment=make_shipment(order,"100",ship_on="2026-10-19");reconcile_order(order.id,self.user.id)
        task=order.tasks.get(kind="domestic_share")
        for step in task.substeps.all():task.refresh_from_db();set_substep(step.id,True,self.user.id,task.row_version)
        task.refresh_from_db();completed_at=task.completed_at
        save_shipment(order.id,ShipmentInput(shipment.id,date(2026,10,21),None,None,{order.lines.first().id:Decimal(100)}),self.user.id,shipment.row_version)
        task.refresh_from_db();self.assertEqual(task.effective_on,date(2026,10,16));self.assertEqual(task.completed_at,completed_at);self.assertTrue(task.needs_review)
    def test_clear_etd_suspends_manual_followup_and_preserves_done(self):
        order=make_order(order_type="overseas",dues=());s=make_shipment(order,"100",etd="2026-10-16");reconcile_order(order.id,self.user.id)
        task=order.tasks.get(kind="overseas_erp");move_task(task.id,date(2026,10,20),self.user.id,task.row_version)
        save_shipment(order.id,ShipmentInput(s.id,None,None,None,{order.lines.first().id:Decimal(100)}),self.user.id,s.row_version)
        task.refresh_from_db();self.assertTrue(task.suspended);self.assertIsNone(task.effective_on);self.assertEqual(task.manual_on,date(2026,10,20))

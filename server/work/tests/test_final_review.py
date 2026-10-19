from dataclasses import replace
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from common.errors import ValidationError
from orders.tests.factories import make_order,make_shipment
from orders.services import save_shipment
from common.contracts import ShipmentInput
from work.services import set_substep,reconcile_order,review_completed_task

class ReworkReviewTests(TestCase):
    def setUp(self):self.user=get_user_model().objects.create_user('review-manager')
    def finish(self,task):
        for step in task.substeps.all():
            set_substep(step.id,True,self.user.id,task.row_version);task.refresh_from_db()
    def test_completed_uncheck_requires_explicit_rework_after_etd_cleared(self):
        order=make_order(order_type='overseas',dues=());s=make_shipment(order,'100',etd='2026-10-16')
        task=order.tasks.get(kind='overseas_erp');self.finish(task)
        save_shipment(order.id,ShipmentInput(s.id,None,None,None,{order.lines.first().id:Decimal(100)}),self.user.id,s.row_version)
        task.refresh_from_db()
        with self.assertRaises(ValidationError):set_substep(task.substeps.first().id,False,self.user.id,task.row_version)
        review_completed_task(task.id,True,self.user.id,task.row_version);task.refresh_from_db()
        self.assertTrue(task.suspended);self.assertIsNone(task.effective_on)
    def test_rework_refreshes_erp_labels_preserving_old_labels_in_audit(self):
        order=make_order();make_shipment(order,'100',ship_on='2026-10-19')
        task=order.tasks.get(kind='domestic_request');self.finish(task)
        old=list(task.substeps.values_list('label',flat=True))
        order.lines.update(currency='USD');reconcile_order(order.id,self.user.id);task.refresh_from_db()
        review_completed_task(task.id,True,self.user.id,task.row_version);task.refresh_from_db()
        self.assertNotEqual(list(task.substeps.values_list('label',flat=True)),old)
        self.assertEqual([s['label'] for s in order.history.get(action='reopen_task').before['steps']],old)

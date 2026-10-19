from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment
from work.services import reconcile_order,set_substep,review_completed_task
from work.queries import get_notice_candidates
from datetime import date
class CompletionTests(TestCase):
    def test_partial_complete_and_reopen_do_not_change_shipped_quantity(self):
        user=get_user_model().objects.create_user("manager");order=make_order(order_type="overseas",dues=());make_shipment(order,"100",etd="2026-10-16");reconcile_order(order.id,user.id)
        task=order.tasks.get(kind="overseas_invoice");steps=list(task.substeps.all())
        set_substep(steps[0].id,True,user.id,task.row_version);task.refresh_from_db();self.assertEqual(task.state,"partial")
        set_substep(steps[1].id,True,user.id,task.row_version);task.refresh_from_db();self.assertEqual(task.state,"done")
        self.assertEqual(order.lines.first().shipped,0)
        self.assertNotIn(task.id,[c.id for c in get_notice_candidates(date(2026,10,20),True)])
        review_completed_task(task.id,True,user.id,task.row_version);task.refresh_from_db();self.assertEqual(task.state,"open");self.assertTrue(all(not s.done for s in task.substeps.all()))
        self.assertTrue(order.history.filter(action="reopen_task").exists())

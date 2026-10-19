from datetime import timedelta,date
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment
from work.services import set_substep,move_task
from notices.models import NoticeSettings,NoticeBatch,SendAttempt
from notices.planner import plan_daily
from notices.worker import dispatch_batch
from notices.providers.fake import FakeSmsProvider
from .test_plan import at

class DispatchTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('manager')
        NoticeSettings.objects.create(id=1,user=self.user,recipient='01012345678',sender='0212345678',enabled=True)
        self.order=make_order();make_shipment(self.order,'100',ship_on='2026-10-19')
        self.batch_id=plan_daily(at())[0]
    def test_completed_or_moved_tasks_excluded_before_send(self):
        a=self.order.tasks.get(kind='domestic_share');set_substep(a.substeps.first().id,True,self.user.id,a.row_version)
        b=self.order.tasks.get(kind='domestic_request');move_task(b.id,date(2026,10,20),self.user.id,b.row_version)
        provider=FakeSmsProvider();dispatch_batch(self.batch_id,provider,at())
        batch=NoticeBatch.objects.get(pk=self.batch_id);self.assertEqual(batch.status,'cancelled');self.assertEqual(SendAttempt.objects.count(),0)
    def test_failure_retries_only_three_times_at_five_minutes(self):
        provider=FakeSmsProvider(outcome='failed')
        dispatch_batch(self.batch_id,provider,at())
        dispatch_batch(self.batch_id,provider,at()+timedelta(minutes=4))
        self.assertEqual(SendAttempt.objects.count(),1)
        for minutes in (5,10,15,20):dispatch_batch(self.batch_id,provider,at()+timedelta(minutes=minutes))
        batch=NoticeBatch.objects.get(pk=self.batch_id);self.assertEqual(batch.status,'failed');self.assertEqual(SendAttempt.objects.count(),4)
    def test_success_is_not_resent(self):
        provider=FakeSmsProvider();dispatch_batch(self.batch_id,provider,at());dispatch_batch(self.batch_id,provider,at(16,10))
        self.assertEqual(SendAttempt.objects.count(),1);self.assertEqual(NoticeBatch.objects.get(pk=self.batch_id).status,'delivered')
    def test_weekend_does_not_send_old_batch(self):
        dispatch_batch(self.batch_id,FakeSmsProvider(),at(17));self.assertEqual(SendAttempt.objects.count(),0)
    def test_changed_work_after_first_part_stops_stale_remaining_parts(self):
        order=self.order;user=self.user
        class ChangesAfterAccept(FakeSmsProvider):
            def send(inner,request):
                result=super().send(request)
                task=order.tasks.get(kind='domestic_request')
                move_task(task.id,date(2026,10,20),user.id,task.row_version)
                return result
        provider=ChangesAfterAccept(byte_limit=130)
        dispatch_batch(self.batch_id,provider,at())
        self.assertEqual(SendAttempt.objects.count(),1)
        batch=NoticeBatch.objects.get(pk=self.batch_id)
        self.assertEqual(batch.status,'failed');self.assertIn('변경',batch.error)
    def test_accepted_part_is_not_retried_when_other_parts_fail(self):
        class PartialProvider(FakeSmsProvider):
            first_key=None
            fail_remaining=True
            def send(inner,request):
                if inner.first_key is None:inner.first_key=request.client_key
                inner.outcome='delivered' if request.client_key==inner.first_key or not inner.fail_remaining else 'failed'
                return super().send(request)
        provider=PartialProvider(byte_limit=150)
        dispatch_batch(self.batch_id,provider,at())
        provider.fail_remaining=False
        dispatch_batch(self.batch_id,provider,at()+timedelta(minutes=5))
        self.assertEqual(NoticeBatch.objects.get(pk=self.batch_id).status,'delivered')
        self.assertEqual(SendAttempt.objects.filter(part__client_key=provider.first_key).count(),1)

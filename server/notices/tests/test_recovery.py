from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment
from notices.models import NoticeSettings,NoticeBatch,NoticePart,SendAttempt
from notices.planner import plan_daily
from notices.worker import dispatch_batch,recover_unknown
from notices.providers.fake import FakeSmsProvider,SimulatedCrash
from .test_plan import at
class RecoveryTests(TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user('manager');NoticeSettings.objects.create(id=1,user=user,recipient='01012345678',sender='0212345678',enabled=True)
        order=make_order();make_shipment(order,'100',ship_on='2026-10-19');self.batch=plan_daily(at())[0]
    def test_accepted_then_process_dies_is_looked_up_not_resent(self):
        provider=FakeSmsProvider(crash_after_accept=True)
        with self.assertRaises(SimulatedCrash):dispatch_batch(self.batch,provider,at())
        recover_unknown(provider,at()+timedelta(minutes=4))
        dispatch_batch(self.batch,provider,at()+timedelta(minutes=5))
        self.assertEqual(SendAttempt.objects.count(),1)
        part=NoticePart.objects.get();self.assertEqual(provider.accepted_count(part.client_key),1)
        self.assertIn(NoticeBatch.objects.get(pk=self.batch).status,['accepted','delivered'])
    def test_unknown_remains_unknown_without_resend(self):
        provider=FakeSmsProvider(outcome='unknown');dispatch_batch(self.batch,provider,at());recover_unknown(provider,at()+timedelta(minutes=4));dispatch_batch(self.batch,provider,at()+timedelta(minutes=5))
        self.assertEqual(SendAttempt.objects.count(),1);self.assertEqual(NoticeBatch.objects.get(pk=self.batch).status,'unknown')

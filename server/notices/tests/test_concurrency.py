from concurrent.futures import ThreadPoolExecutor
from django.test import TransactionTestCase
from django.db import connections
from django.contrib.auth import get_user_model
from notices.models import NoticeSettings,SendAttempt
from notices.planner import plan_daily
from notices.worker import dispatch_batch
from notices.providers.fake import FakeSmsProvider
from orders.tests.factories import make_order,make_shipment
from .test_plan import at
class WorkerConcurrencyTests(TransactionTestCase):
    def test_two_workers_do_not_send_twice(self):
        user=get_user_model().objects.create_user('manager');NoticeSettings.objects.create(id=1,user=user,recipient='01012345678',sender='0212345678',enabled=True)
        order=make_order();make_shipment(order,'100',ship_on='2026-10-19');batch=plan_daily(at())[0];provider=FakeSmsProvider()
        def dispatch(_):
            try:return dispatch_batch(batch,provider,at())
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(dispatch,[1,2]))
        self.assertEqual(SendAttempt.objects.count(),1)

from unittest.mock import patch
from django.test import TestCase,TransactionTestCase
from django.contrib.auth import get_user_model
from orders.models import ChangeEvent
from orders.tests.factories import make_order,make_shipment
from notices.models import NoticeSettings,NoticeBatch
from notices.planner import plan_daily,consume_changes
from .test_plan import at

class EventOrderTests(TestCase):
    def test_later_visible_lower_sequence_event_is_still_consumed(self):
        user=get_user_model().objects.create_user('review-manager')
        NoticeSettings.objects.create(id=1,user=user,recipient='01012345678',sender='0212345678',enabled=True)
        plan_daily(at());consume_changes(at())
        with patch('django.utils.timezone.now',return_value=at(16,10)):
            a=make_order();make_shipment(a,'100',ship_on='2026-10-19')
            b=make_order();make_shipment(b,'100',ship_on='2026-10-19')
        event=ChangeEvent.objects.filter(order=a).first()
        saved={f.name:getattr(event,f.name) for f in event._meta.fields}
        # Hold the lower sequence event out of visibility until the higher one is consumed.
        event.delete()
        self.assertEqual(len(consume_changes(at(16,10))),1)
        ChangeEvent.objects.create(**saved)
        self.assertEqual(len(consume_changes(at(16,10,1))),1)
        self.assertEqual(consume_changes(at(16,10,2)),())

class ConcurrentCommitTests(TransactionTestCase):
    def test_lower_sequence_committing_after_consumer_is_not_lost(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from django.db import transaction,connections
        user=get_user_model().objects.create_user('review-manager')
        NoticeSettings.objects.create(id=1,user=user,recipient='01012345678',sender='0212345678',enabled=True)
        plan_daily(at());consume_changes(at())
        inserted=Event();release=Event()
        def delayed():
            try:
                with transaction.atomic():
                    order=make_order();make_shipment(order,'100',ship_on='2026-10-19')
                    inserted.set()
                    if not release.wait(20):raise RuntimeError('test coordination timed out')
                return order.id
            finally:connections.close_all()
        with patch('django.utils.timezone.now',return_value=at(16,10)):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(delayed)
                try:
                    self.assertTrue(inserted.wait(10))
                    other=make_order();make_shipment(other,'100',ship_on='2026-10-19')
                    self.assertEqual(len(consume_changes(at(16,10))),1)
                finally:release.set()
                order_id=future.result(timeout=10)
            self.assertEqual(len(consume_changes(at(16,10,1))),1)
        self.assertEqual(NoticeBatch.objects.filter(items__task__order_id=order_id).distinct().count(),1)

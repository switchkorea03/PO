from datetime import datetime,date
from zoneinfo import ZoneInfo
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment
from work.services import set_substep,move_task
from notices.models import NoticeSettings,NoticeBatch,NoticeItem
from notices.planner import plan_daily,consume_changes
from notices.renderer import render_notice
from work.queries import get_notice_candidates

KST=ZoneInfo('Asia/Seoul')
def at(day=16,hour=9,minute=0):return datetime(2026,10,day,hour,minute,tzinfo=KST)

class DailyPlanTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('manager')
        self.settings=NoticeSettings.objects.create(id=1,user=self.user,recipient='01012345678',sender='0212345678',enabled=True)
        with patch('django.utils.timezone.now',return_value=at(16,8)):
            self.order=make_order();make_shipment(self.order,'100',ship_on='2026-10-19')
    def test_daily_once_at_nine_and_weekends_excluded(self):
        self.assertEqual(plan_daily(at(16,8,59)),())
        self.assertEqual(len(plan_daily(at())),1)
        self.assertEqual(plan_daily(at(16,9,1)),())
        self.assertEqual(plan_daily(at(17)),())
        batch=NoticeBatch.objects.get();self.assertEqual(batch.items.count(),2)
    def test_overdue_and_partial_steps_only(self):
        task=self.order.tasks.get(kind='domestic_request');step=task.substeps.first()
        set_substep(step.id,True,self.user.id,task.row_version)
        body=render_notice(get_notice_candidates(date(2026,10,19),True),date(2026,10,19))
        self.assertIn('오늘',body);self.assertIn('지연',body);self.assertIn('범진전자',body)
        self.assertNotIn(step.label,body)
    def test_new_today_task_after_daily_gets_one_extra(self):
        plan_daily(at());batch=NoticeBatch.objects.get();batch.status='delivered';batch.save()
        with patch('django.utils.timezone.now',return_value=at(16,10)):
            other=make_order();make_shipment(other,'100',ship_on='2026-10-19')
        extras=consume_changes(at(16,10))
        self.assertEqual(len(extras),1)
        self.assertEqual(NoticeBatch.objects.get(pk=extras[0]).items.count(),2)
        self.assertEqual(consume_changes(at(16,10,1)),())
    def test_save_or_partial_check_does_not_generate_extra(self):
        plan_daily(at());NoticeBatch.objects.update(status='delivered')
        with patch('django.utils.timezone.now',return_value=at(16,10)):
            task=self.order.tasks.get(kind='domestic_request');set_substep(task.substeps.first().id,True,self.user.id,task.row_version)
        self.assertEqual(consume_changes(at(16,10)),())

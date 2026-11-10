from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment
from work.views import calendar_data
from work.queries import dashboard_summary


class CompanyCountTests(TestCase):
    def test_calendar_counts_customers_instead_of_items_or_pos(self):
        get_user_model().objects.create_user('company-counter')
        first=make_order(dues=('2026-11-17',))
        make_shipment(first,'50',ship_on='2026-11-17');make_shipment(first,'50',ship_on='2026-11-17')
        second=make_order(dues=('2026-11-17',));second.customer=first.customer;second.save()
        make_shipment(second,'100',ship_on='2026-11-17')
        data=calendar_data(date(2026,11,17),date(2026,11,17))
        group=next(value for value in data['groups'] if value['kind']=='domestic_excel')
        self.assertEqual(group['customer_count'],1)
        self.assertNotIn('3건',group['title'])
        self.assertEqual(len(group['tasks']),3)
        self.assertEqual(len(data['due_markers']),1)
        self.assertEqual(len(data['due_markers'][0]['order_ids']),2)
        self.assertEqual(dashboard_summary(date(2026,11,17))['today'],1)
        third=make_order(dues=('2026-11-17',));make_shipment(third,'100',ship_on='2026-11-17')
        data=calendar_data(date(2026,11,17),date(2026,11,17))
        group=next(value for value in data['groups'] if value['kind']=='domestic_excel')
        self.assertEqual(group['customer_count'],2);self.assertIn('2건',group['title'])
        self.assertEqual(dashboard_summary(date(2026,11,17))['today'],2)

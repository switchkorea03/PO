from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment

class DashboardTests(TestCase):
    def test_live_counts_follow_status_and_customer_filters(self):
        from work.queries import dashboard_summary
        get_user_model().objects.create_user('dashboard-manager')
        domestic=make_order();make_shipment(domestic,'100',ship_on='2026-10-19')
        overseas=make_order(order_type='overseas',dues=());make_shipment(overseas,'100')
        summary=dashboard_summary(date(2026,10,19))
        self.assertEqual(summary,{'today':4,'overdue':2,'open_orders':2,'undated_shipments':1})
        scoped=dashboard_summary(date(2026,10,19),domestic.customer_id,'domestic')
        self.assertEqual(scoped,{'today':3,'overdue':2,'open_orders':1,'undated_shipments':0})
        domestic.tasks.filter(kind='domestic_share').update(state='done')
        domestic.tasks.filter(kind='domestic_request').update(suspended=True)
        self.assertEqual(dashboard_summary(date(2026,10,19))['overdue'],0)

    def test_cancelled_orders_do_not_count_as_pending_work(self):
        from work.queries import dashboard_summary
        get_user_model().objects.create_user('dashboard-manager')
        o=make_order();make_shipment(o,'100',ship_on='2026-10-19');o.cancelled=True;o.save()
        self.assertEqual(dashboard_summary(date(2026,10,19)),{'today':0,'overdue':0,'open_orders':0,'undated_shipments':0})

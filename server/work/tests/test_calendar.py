import json
from datetime import date
from django.test import TestCase,Client
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment
from work.services import reconcile_order
from work.queries import get_notice_candidates
class CalendarTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user("manager",password="testing-pass-123")
        self.client.force_login(self.user)
    def test_share_group_preserves_three_tasks(self):
        for customer in ("A","B","A"):
            o=make_order();o.customer.name=customer;o.customer.save();make_shipment(o,"100",ship_on="2026-10-19")
        response=self.client.get("/api/calendar/?start=2026-10-16&end=2026-10-19")
        self.assertEqual(response.status_code,200)
        groups=response.json()["groups"]
        group=next(g for g in groups if g["kind"]=="domestic_share")
        self.assertEqual(group["title"],"A,B(출고 내역 공유)")
        self.assertEqual(len(group["tasks"]),3)
    def test_due_is_not_checkable_or_a_notice_candidate(self):
        domestic=make_order();make_shipment(domestic,"100",ship_on="2026-10-19")
        overseas=make_order(order_type="overseas");make_shipment(overseas,"100",etd="2026-10-16")
        data=self.client.get("/api/calendar/?start=2026-10-16&end=2026-10-20").json()
        self.assertEqual(len(data["due_markers"]),1)
        self.assertFalse(data["due_markers"][0]["checkable"])
        self.assertNotIn(data["due_markers"][0]["id"],[str(c.id) for c in get_notice_candidates(date(2026,10,20),True)])
    def test_stale_task_returns_409_and_csrf_is_required(self):
        o=make_order();make_shipment(o,"100",ship_on="2026-10-19");t=o.tasks.first()
        response=self.client.post(f"/tasks/{t.id}/move/",data=json.dumps({"target_on":"2026-10-20","row_version":999}),content_type="application/json")
        self.assertEqual(response.status_code,409)
        strict=Client(enforce_csrf_checks=True);strict.force_login(self.user)
        self.assertEqual(strict.post(f"/tasks/{t.id}/move/",data={}).status_code,403)
    def test_filter_and_invalid_range(self):
        a=make_order();b=make_order();make_shipment(a,"100",ship_on="2026-10-19");make_shipment(b,"100",ship_on="2026-10-19")
        response=self.client.get(f"/api/calendar/?start=2026-10-16&end=2026-10-20&customer={a.customer_id}")
        self.assertEqual(len(response.json()["tasks"]),5)
        self.assertEqual(self.client.get("/api/calendar/?start=bad&end=2026-10-20").status_code,422)

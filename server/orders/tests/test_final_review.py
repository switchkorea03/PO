from dataclasses import replace
from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from common.contracts import OrderInput, LineInput
from orders.models import AuditEntry
from orders import services
from orders.tests.factories import make_order, make_shipment

class FinalReviewTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('review-manager')

    def test_cancel_one_round_releases_quantity_and_preserves_other_round(self):
        order=make_order(); first=make_shipment(order,'70',ship_on='2026-10-19'); second=make_shipment(order,'30',ship_on='2026-10-20')
        services.cancel_shipment(first.id,'고객 취소',self.user.id,first.row_version)
        first.refresh_from_db(); second.refresh_from_db(); order.refresh_from_db()
        self.assertTrue(first.cancelled);self.assertFalse(second.cancelled)
        self.assertFalse(order.cancelled)
        line=order.lines.first()
        services.cancel_remaining(line.id,Decimal(70),self.user.id,order.row_version)
        self.assertEqual(line.allocated,30)
        self.assertFalse(order.tasks.filter(shipment=first).exclude(state='cancelled').exists())

    def test_order_audit_retains_complete_before_and_after(self):
        order=make_order();line=order.lines.first()
        data=OrderInput(order.customer_id,order.po_number,'domestic',contact='새 담당자',note='변경',lines=(LineInput(line.id,'NEW','새 품명',line.quantity,'BOX',Decimal('1.25'),'USD',requested_due=line.requested_due),))
        services.save_order(data,self.user.id,order.row_version,order.id)
        entry=AuditEntry.objects.get(action='save_order')
        self.assertEqual(Decimal(entry.before['lines'][0]['unit_price']),Decimal('.2'))
        self.assertEqual(Decimal(entry.after['lines'][0]['unit_price']),Decimal('1.25'))
        self.assertEqual(entry.after['contact'],'새 담당자')
        self.assertEqual(entry.after['lines'][0]['currency'],'USD')

    def test_completed_shipment_eta_can_be_updated_without_quantity_change(self):
        order=make_order(order_type='overseas',dues=());s=make_shipment(order,'100',etd='2026-10-16')
        services.confirm_shipment(s.id,self.user.id,s.row_version);s.refresh_from_db()
        services.update_eta(s.id,date(2026,10,25),self.user.id,s.row_version)
        s.refresh_from_db();self.assertEqual(s.eta,date(2026,10,25));self.assertTrue(s.completed)
        self.assertEqual(order.lines.first().shipped,100)

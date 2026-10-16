from datetime import date
from decimal import Decimal
from dataclasses import replace
from django.test import TestCase
from django.contrib.auth import get_user_model
from common.contracts import OrderInput, LineInput, ShipmentInput
from common.errors import AllocationExceeded, ValidationError, VersionConflict
from orders.models import Customer, Order, AuditEntry
from orders.services import save_order,save_shipment,confirm_shipment,cancel_remaining,correct_shipment,cancel_order
from .factories import make_order,make_shipment
class QuantityTests(TestCase):
    def setUp(self): self.user=get_user_model().objects.create_user("manager")
    def test_single_quantity_and_confirmation(self):
        order=make_order();line=order.lines.first()
        first=make_shipment(order,"70",ship_on="2026-10-19");make_shipment(order,"30",ship_on="2026-10-20")
        self.assertEqual(line.shipped,0);self.assertEqual(line.remaining,100)
        confirm_shipment(first.id,self.user.id,first.row_version)
        self.assertEqual(line.shipped,70);self.assertEqual(line.remaining,30)
        confirm_shipment(first.id,self.user.id,first.row_version)
        self.assertEqual(line.shipped,70)
    def test_overallocation_and_reduction(self):
        order=make_order();first=make_shipment(order,"70",ship_on="2026-10-19")
        with self.assertRaises(AllocationExceeded):make_shipment(order,"40",ship_on="2026-10-20")
        confirm_shipment(first.id,self.user.id,first.row_version);order.refresh_from_db();line=order.lines.first()
        data=OrderInput(order.customer_id,order.po_number,"domestic",received_on=order.received_on,lines=(LineInput(line.id,line.code,line.name,Decimal(60),"EA",requested_due=line.requested_due),))
        with self.assertRaises(AllocationExceeded):save_order(data,self.user.id,order.row_version,order.id)
        line.refresh_from_db();self.assertEqual(line.quantity,100)
    def test_cancel_and_correction(self):
        order=make_order();first=make_shipment(order,"70",ship_on="2026-10-19")
        confirm_shipment(first.id,self.user.id,first.row_version);order.refresh_from_db();line=order.lines.first()
        cancel_remaining(line.id,Decimal(30),self.user.id,order.row_version);line.refresh_from_db()
        self.assertEqual(line.shipped,70);self.assertEqual(line.cancelled_quantity,30);self.assertEqual(line.remaining,0)
        first.refresh_from_db()
        with self.assertRaises(ValidationError):correct_shipment(first.id,{line.id:Decimal(65)},"",self.user.id,first.row_version)
        correct_shipment(first.id,{line.id:Decimal(65)},"수량 정정",self.user.id,first.row_version)
        self.assertEqual(line.shipped,65);self.assertEqual(line.remaining,5)
        self.assertTrue(AuditEntry.objects.filter(reason="수량 정정").exists())
    def test_default_shipments_group_only_within_po(self):
        customer=Customer.objects.create(name="A")
        lines=tuple(LineInput(None,str(i),f"품목{i}",Decimal(10),"EA",requested_due=date(2026,10,19 if i<2 else 20)) for i in range(3))
        order=save_order(OrderInput(customer.id,"A-1","domestic",lines=lines),self.user.id,None)
        self.assertEqual(order.shipments.count(),2)
        self.assertEqual(sorted(s.allocations.count() for s in order.shipments.all()),[1,2])
    def test_missing_domestic_date_and_nonfinite_quantity_rejected(self):
        customer=Customer.objects.create(name="A")
        for quantity,due in [(Decimal(1),None),(Decimal('NaN'),date(2026,10,19))]:
            with self.assertRaises(ValidationError):save_order(OrderInput(customer.id,"A-1","domestic",lines=(LineInput(None,"A","품목",quantity,"EA",requested_due=due),)),self.user.id,None)
    def test_wrong_po_line_and_stale_version(self):
        a=make_order();b=make_order();s=make_shipment(a,"50",ship_on="2026-10-19")
        with self.assertRaises(ValidationError):save_shipment(a.id,ShipmentInput(s.id,date(2026,10,19),None,None,{b.lines.first().id:Decimal(10)}),self.user.id,s.row_version)
        with self.assertRaises(VersionConflict):save_shipment(a.id,ShipmentInput(s.id,date(2026,10,19),None,None,{a.lines.first().id:Decimal(10)}),self.user.id,999)
    def test_cancel_preserves_completed_shipment(self):
        order=make_order();s=make_shipment(order,"70",ship_on="2026-10-19");confirm_shipment(s.id,self.user.id,s.row_version);order.refresh_from_db()
        cancel_order(order.id,self.user.id,order.row_version);s.refresh_from_db()
        self.assertTrue(s.completed);self.assertFalse(s.cancelled)

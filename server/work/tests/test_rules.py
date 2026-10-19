from datetime import date, timedelta
from uuid import uuid4
from decimal import Decimal
from django.test import SimpleTestCase
from common.contracts import OrderSnapshot,ShipmentInput,LineInput
from work.rules import next_week_tuesday,next_weekday,previous_weekday,build_task_specs
class DateRulesTests(SimpleTestCase):
    def test_weekends_and_original_receipt_week(self):
        self.assertEqual(previous_weekday(date(2026,10,19)),date(2026,10,16))
        self.assertEqual(next_week_tuesday(date(2026,10,18)),date(2026,10,20))
        self.assertEqual(next_week_tuesday(date(2026,10,19)),date(2026,10,27))
        for day in (16,17,18):self.assertEqual(next_weekday(date(2026,10,day)+timedelta(days=1)),date(2026,10,19))
    def test_year_boundary_and_leap_day(self):
        self.assertEqual(next_week_tuesday(date(2026,12,31)),date(2027,1,5))
        self.assertEqual(previous_weekday(date(2028,2,29)),date(2028,2,28))
    def test_domestic_five_tasks_per_shipment(self):
        sid=uuid4();oid=uuid4();lid=uuid4()
        snap=OrderSnapshot(oid,"domestic","unspecified","USD",None,(LineInput(lid,"A","품목",Decimal(1),"EA",currency="USD",requested_due=date(2026,10,19)),),(ShipmentInput(sid,date(2026,10,19),None,None,{lid:Decimal(1)}),))
        specs=build_task_specs(snap)
        self.assertEqual(len(specs),5)
        self.assertEqual(sum(s.auto_on==date(2026,10,16) for s in specs),2)
        self.assertTrue(any("출고의뢰등록(수출)" in step for s in specs for step in s.substeps))
    def test_overseas_uses_etd_not_eta_or_due(self):
        oid=uuid4();sid=uuid4();lid=uuid4()
        snap=OrderSnapshot(oid,"overseas","export","USD",date(2026,10,18),(),(ShipmentInput(sid,None,None,date(2026,11,1),{lid:Decimal(1)}),))
        specs=build_task_specs(snap)
        self.assertEqual(len(specs),5)
        self.assertEqual([s.auto_on for s in specs[:2]],[date(2026,10,19),date(2026,10,20)])
        self.assertEqual(sum(s.auto_on is None for s in specs),3)
        self.assertFalse(any("납기" in s.title for s in specs))
    def test_other_currency_requires_explicit_erp_selection(self):
        oid=uuid4();sid=uuid4()
        specs=build_task_specs(OrderSnapshot(oid,"domestic","unspecified","EUR",None,(),(ShipmentInput(sid,date(2026,10,19),None,None,{}),)))
        self.assertTrue(any("거래유형" in step for s in specs for step in s.substeps))

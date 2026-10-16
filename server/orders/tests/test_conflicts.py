from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connections
from common.contracts import ShipmentInput
from common.errors import AllocationExceeded
from orders.services import save_shipment
from .factories import make_order
class ConflictTests(TransactionTestCase):
    def test_concurrent_allocations_do_not_exceed_order(self):
        user=get_user_model().objects.create_user("manager");order=make_order();line=order.lines.first()
        def allocate(q):
            try:
                save_shipment(order.id,ShipmentInput(None,date(2026,10,19),None,None,{line.id:Decimal(q)}),user.id,None)
                return "ok"
            except AllocationExceeded:return "rejected"
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(allocate,["70","40"]))
        self.assertEqual(sorted(results),["ok","rejected"])
        self.assertLessEqual(line.allocated,100)

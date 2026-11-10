from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment
from inventory.queries import inventory_rows


class InventoryTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('stock-reader')

    def test_login_and_disconnected_page_do_not_claim_live_inventory(self):
        self.assertEqual(self.client.get('/inventory/').status_code,302)
        self.client.force_login(self.user)
        response=self.client.get('/inventory/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'재고 확인')
        self.assertContains(response,'ERP 미연결')
        self.assertContains(response,'재고 수량은 아직 조회되지 않았습니다')
        self.assertContains(response,'disabled')
        self.assertNotContains(response,'재고 동기화 완료')

    def test_remaining_quantities_and_units_are_independent_of_unknown_stock(self):
        order=make_order(quantities=('100',),dues=('2026-11-17',))
        line=order.lines.first();line.internal_name='JTP1135JEM';line.save()
        shipment=make_shipment(order,'30',ship_on='2026-11-17');shipment.completed=True;shipment.save()
        line.cancelled_quantity=Decimal('10');line.save()
        other=make_order(quantities=('7',));second=other.lines.first();second.internal_name='JTP1135JEM';second.unit='BOX';second.save()
        ignored=make_order();ignored.is_deleted=True;ignored.save()
        ignored_line=ignored.lines.first();ignored_line.internal_name='JTP1135JEM';ignored_line.save()
        rows=inventory_rows('JTP1135JEM')
        self.assertEqual({row['unit']:row['remaining'] for row in rows},{'EA':Decimal('60'),'BOX':Decimal('7')})
        self.assertTrue(all(row['stock'].on_hand is None and row['stock'].available is None for row in rows))
        self.assertTrue(all(row['stock'].observed_at is None for row in rows))

    def test_cancelled_orders_are_excluded_and_search_matches_customer_item(self):
        order=make_order();line=order.lines.first();line.internal_name='JT1138BEM';line.code='CUSTOMER-STOCK';line.save()
        self.assertEqual(inventory_rows('CUSTOMER-STOCK')[0]['item_name'],'JT1138BEM')
        order.cancelled=True;order.save()
        self.assertEqual(inventory_rows('JT1138BEM')[0]['remaining'],Decimal('0'))
        self.assertEqual(inventory_rows('no-such-stock-item'),[])

    def test_reference_aliases_and_customer_codes_are_searchable_without_po(self):
        self.assertEqual(inventory_rows('SKRWAEE030')[0]['item_name'],'JTP1135JEM')
        self.assertEqual(inventory_rows('MESA100005A')[0]['item_name'],'JT1138BEM')

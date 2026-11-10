from io import BytesIO
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from openpyxl import load_workbook
from orders.services import delete_order
from .factories import make_order


class OrderExportTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('export-manager')
        self.client.force_login(self.user)

    def workbook(self,url='/orders/export.xlsx'):
        response=self.client.get(url)
        self.assertEqual(response.status_code,200)
        self.assertIn('attachment',response['Content-Disposition'])
        return load_workbook(BytesIO(b''.join(response.streaming_content)))

    def test_export_matches_filters_and_has_numeric_rows_for_each_item(self):
        order=make_order(quantities=('1000','2000'))
        make_order('overseas')
        deleted=make_order();delete_order(deleted.id,self.user.id,deleted.row_version)
        workbook=self.workbook(f'/orders/export.xlsx?customer={order.customer_id}&type=domestic&q={order.po_number}')
        sheet=workbook.active;rows=list(sheet.values)
        self.assertEqual(sheet.title,'PO 목록')
        self.assertEqual(len(rows),3)
        self.assertEqual([row[3] for row in rows[1:]],[order.po_number]*2)
        self.assertEqual(sorted(row[7] for row in rows[1:]),[1000,2000])
        self.assertEqual(sorted(row[10] for row in rows[1:]),[200,400])
        self.assertEqual(sheet.freeze_panes,'A2')
        self.assertEqual(sheet.auto_filter.ref,'A1:P3')
        workbook.close()

    def test_deleted_orders_only_export_when_trash_is_selected(self):
        active=make_order();deleted=make_order()
        delete_order(deleted.id,self.user.id,deleted.row_version)
        normal=self.workbook();trash=self.workbook('/orders/export.xlsx?state=deleted')
        self.assertEqual([row[3] for row in list(normal.active.values)[1:]],[active.po_number])
        self.assertEqual([row[3] for row in list(trash.active.values)[1:]],[deleted.po_number])
        normal.close();trash.close()

    def test_user_text_is_not_a_formula_and_large_decimals_keep_precision(self):
        order=make_order(quantities=('12345678901234567890.1234567890',))
        order.po_number='=1+1';order.save()
        line=order.lines.get();line.code='=SUM(1,2)';line.save()
        workbook=self.workbook();sheet=workbook.active
        self.assertEqual(sheet['D2'].value,'=1+1')
        self.assertEqual(sheet['D2'].data_type,'s')
        self.assertEqual(sheet['F2'].value,'=SUM(1,2)')
        self.assertEqual(sheet['F2'].data_type,'s')
        self.assertEqual(Decimal(sheet['H2'].value),line.quantity)
        self.assertEqual(sheet['H2'].data_type,'s')
        workbook.close()

    def test_empty_export_and_login_requirement(self):
        workbook=self.workbook('/orders/export.xlsx?q=NOT-FOUND')
        self.assertEqual(workbook.active.max_row,1)
        workbook.close()
        self.client.logout()
        self.assertEqual(self.client.get('/orders/export.xlsx').status_code,302)

    def test_small_decimal_amount_has_enough_display_places(self):
        order=make_order(quantities=('0.0000000001',))
        line=order.lines.get();line.unit_price=Decimal('0.0000000001');line.save()
        workbook=self.workbook();cell=workbook.active['K2']
        self.assertEqual(cell.value,1e-20)
        self.assertEqual(cell.number_format,'#,##0.'+'#'*20)
        workbook.close()

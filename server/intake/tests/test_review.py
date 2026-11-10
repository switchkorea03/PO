import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from common.contracts import OrderInput,LineInput
from orders.models import Order,Customer
from intake.services import upload_source,confirm_draft
from intake.worker import process_extraction
from .test_upload import excel_bytes

class ReviewTests(TestCase):
    def test_customer_item_and_spec_headers_map_to_editable_fields(self):
        import io
        from openpyxl import Workbook
        workbook=Workbook();sheet=workbook.active
        sheet.append(['고객품목명','스펙','수량','단위','단가','공급가액','납기일'])
        sheet.append(['MESA100005A','MCU 32BIT',1000,'EA',1500,1500000,'2026-10-29'])
        content=io.BytesIO();workbook.save(content)
        uploaded=upload_source(SimpleUploadedFile('labels.xlsx',content.getvalue()),self.user.id)
        draft=process_extraction(uploaded.job_id)
        self.assertEqual(draft.result['lines'][0]['code']['value'],'MESA100005A')
        self.assertEqual(draft.result['lines'][0]['name']['value'],'MCU 32BIT')

    def setUp(self):
        self.user=get_user_model().objects.create_user('manager');self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.override=override_settings(PRIVATE_MEDIA_ROOT=Path(self.tmp.name));self.override.enable();self.addCleanup(self.override.disable)
    def test_extract_review_then_confirm_is_idempotent(self):
        uploaded=upload_source(SimpleUploadedFile('sample.xlsx',excel_bytes()),self.user.id)
        draft=process_extraction(uploaded.job_id)
        self.assertEqual(Order.objects.count(),0)
        self.assertEqual(draft.result['lines'][0]['quantity']['value'],'100')
        customer=Customer.objects.create(name='테스트고객')
        data=OrderInput(customer.id,'UPLOAD-1','domestic',lines=(LineInput(None,'PART-1','부품',Decimal('70'),'EA',Decimal('.2'),'KRW',Decimal(20),date(2026,10,19)),))
        order=confirm_draft(draft.id,data,self.user.id,None,None,draft.row_version)
        repeated=confirm_draft(draft.id,data,self.user.id,None,None,draft.row_version)
        self.assertEqual(order.id,repeated.id);self.assertEqual(Order.objects.count(),1)
        self.assertTrue(order.lines.first().amount_mismatch)
        self.assertEqual(order.source_versions.count(),1)
        self.assertEqual(order.tasks.count(),5)
    def test_failed_extraction_still_supports_manual_registration(self):
        uploaded=upload_source(SimpleUploadedFile('bad.pdf',b'%PDF-1.4\nnot-readable'),self.user.id)
        draft=process_extraction(uploaded.job_id)
        self.assertEqual(draft.result['status'],'failed')
        self.assertTrue(any('수동입력' in w for w in draft.result['warnings']))

    def test_revision_has_explicit_mapping_for_changed_or_missing_codes(self):
        from orders.tests.factories import make_order,make_shipment
        from orders.services import confirm_shipment
        order=make_order();line=order.lines.first();line.code='';line.save()
        shipment=make_shipment(order,'100',ship_on='2026-10-19')
        confirm_shipment(shipment.id,self.user.id,shipment.row_version);order.refresh_from_db()
        uploaded=upload_source(SimpleUploadedFile('revision.xlsx',excel_bytes()),self.user.id)
        draft=process_extraction(uploaded.job_id)
        self.client.force_login(self.user)
        response=self.client.get(f'/intake/{draft.id}/review/?target={order.id}')
        self.assertEqual(response.context['initial_data']['revision_lines'][0]['id'],str(line.id))
        data=OrderInput(order.customer_id,order.po_number,'domestic',lines=(LineInput(line.id,'CHANGED','품목 수정',Decimal(100),'EA',requested_due=line.requested_due),))
        confirm_draft(draft.id,data,self.user.id,order.id,order.row_version,draft.row_version)
        shipment.refresh_from_db();self.assertTrue(shipment.completed)
        self.assertEqual(shipment.allocations.get().line_id,line.id)
        self.assertEqual(order.lines.get().code,'CHANGED')

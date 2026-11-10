import io
import os
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from common.errors import ValidationError
from intake.services import upload_source


def png_bytes():
    image = Image.new('RGB',(1800,900),'white')
    draw = ImageDraw.Draw(image)
    draw.text((80,100),'PO No: PNG-100',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',50),fill='black')
    output=io.BytesIO();image.save(output,format='PNG');return output.getvalue()


class PngUploadTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('png-manager')
        self.client.force_login(self.user)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.override=override_settings(PRIVATE_MEDIA_ROOT=Path(self.tmp.name));self.override.enable();self.addCleanup(self.override.disable)

    def test_png_upload_preview_and_duplicate_use_private_source(self):
        content=png_bytes()
        first=upload_source(SimpleUploadedFile('PO.PNG',content,content_type='image/png'),self.user.id)
        second=upload_source(SimpleUploadedFile('copy.png',content),self.user.id)
        self.assertEqual(first.source_id,second.source_id)
        response=self.client.get(f'/sources/{first.source_id}/preview/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Content-Type'],'image/png')
        self.assertEqual(b''.join(response.streaming_content),content)
        self.client.logout()
        self.assertEqual(self.client.get(f'/sources/{first.source_id}/preview/').status_code,302)

    def test_spoofed_or_truncated_png_is_rejected(self):
        for content in [b'<html>not PNG</html>',b'\x89PNG\r\n\x1a\nBAD']:
            with self.assertRaises(ValidationError):
                upload_source(SimpleUploadedFile('bad.png',content),self.user.id)

    def test_png_worker_uses_real_local_ocr(self):
        engine=os.getenv('TESSERACT_CMD')
        if not engine or not Path(engine).exists():self.skipTest('로컬 Tesseract 엔진 미설치')
        from intake.worker import process_extraction
        uploaded=upload_source(SimpleUploadedFile('ocr.png',png_bytes()),self.user.id)
        draft=process_extraction(uploaded.job_id)
        self.assertEqual(draft.result['fields']['po_number']['value'],'PNG-100')

    def test_reupload_deleted_source_requires_review_and_save_before_restore(self):
        from intake.models import OrderSource
        from orders.tests.factories import make_order
        from orders.services import delete_order
        content=png_bytes();upload=upload_source(SimpleUploadedFile('existing.png',content),self.user.id)
        order=make_order()
        OrderSource.objects.create(order=order,source_id=upload.source_id,version=1,confirmed_by=self.user)
        delete_order(order.id,self.user.id,order.row_version)
        response=self.client.post('/intake/upload/',{'file':SimpleUploadedFile('copy.png',content)},follow=True)
        self.assertRedirects(response,f'/orders/{order.id}/reregister/')
        self.assertContains(response,'PO 저장')
        initial=response.context['initial_data']
        self.assertEqual(initial['po_number'],order.po_number)
        self.assertEqual(initial['lines'][0]['id'],str(order.lines.get().id))
        order.refresh_from_db()
        self.assertTrue(order.is_deleted)
        self.assertFalse(order.history.filter(action='restore_order').exists())
        initial['note']='다시 확인한 비고'
        initial['lines'][0]['internal_name']='재확인품목'
        saved=self.client.post(f'/orders/{order.id}/reregister/',initial,content_type='application/json')
        self.assertEqual(saved.status_code,200)
        self.assertEqual(saved.json()['url'],f'/orders/{order.id}/')
        order.refresh_from_db()
        self.assertFalse(order.is_deleted)
        self.assertIsNone(order.deleted_at)
        self.assertEqual(order.note,'다시 확인한 비고')
        self.assertEqual(order.lines.get().internal_name,'재확인품목')
        self.assertEqual(order.source_versions.count(),1)
        self.assertTrue(order.history.filter(action='delete_order').exists())
        self.assertTrue(order.history.filter(action='restore_order').exists())
        self.assertContains(self.client.get('/orders/'),order.po_number)
        # A second upload must not create another PO or restore it twice.
        again=self.client.post('/intake/upload/',{'file':SimpleUploadedFile('again.png',content)})
        self.assertContains(again,'이미 등록된 파일입니다')
        self.assertEqual(order.history.filter(action='restore_order').count(),1)

    def test_invalid_reregistration_keeps_po_in_trash(self):
        from orders.tests.factories import make_order
        from orders.services import delete_order
        order=make_order();delete_order(order.id,self.user.id,order.row_version)
        response=self.client.get(f'/orders/{order.id}/reregister/')
        self.assertEqual(response.status_code,200)
        data=response.context['initial_data'];data['lines'][0]['quantity']='0'
        saved=self.client.post(f'/orders/{order.id}/reregister/',data,content_type='application/json')
        self.assertEqual(saved.status_code,422)
        order.refresh_from_db();self.assertTrue(order.is_deleted)
        self.assertFalse(order.history.filter(action='restore_order').exists())

    def test_active_duplicate_source_remains_blocked(self):
        from intake.models import OrderSource
        from orders.tests.factories import make_order
        content=png_bytes();upload=upload_source(SimpleUploadedFile('existing.png',content),self.user.id)
        order=make_order()
        OrderSource.objects.create(order=order,source_id=upload.source_id,version=1,confirmed_by=self.user)
        response=self.client.post('/intake/upload/',{'file':SimpleUploadedFile('copy.png',content)})
        self.assertContains(response,'이미 등록된 파일입니다')
        self.assertFalse(order.history.filter(action='restore_order').exists())

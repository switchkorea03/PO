import tempfile
from pathlib import Path
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from intake.services import upload_source

class SourcePreviewTests(TestCase):
    def test_pdf_preview_requires_login_and_stays_same_origin(self):
        user=get_user_model().objects.create_user('preview-manager')
        with tempfile.TemporaryDirectory() as directory,override_settings(PRIVATE_MEDIA_ROOT=Path(directory)):
            result=upload_source(SimpleUploadedFile('po.pdf',b'%PDF-1.4\nfixture'),user.id)
            url=f'/sources/{result.source_id}/preview/'
            self.assertEqual(self.client.get(url).status_code,302)
            self.client.force_login(user);response=self.client.get(url)
            try:
                self.assertEqual(response.status_code,200)
                self.assertEqual(response['Content-Type'],'application/pdf')
                self.assertTrue(response['Content-Disposition'].startswith('inline;'))
                self.assertEqual(response['X-Frame-Options'],'SAMEORIGIN')
            finally:b''.join(response.streaming_content)

    def test_rendered_pdf_pages_are_private_and_bounded(self):
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from PIL import Image
        user=get_user_model().objects.create_user('page-manager')
        data=BytesIO();pdf=canvas.Canvas(data)
        for n in range(2):pdf.drawString(30,800,f'Page {n+1}');pdf.showPage()
        pdf.save()
        with tempfile.TemporaryDirectory() as directory,override_settings(PRIVATE_MEDIA_ROOT=Path(directory)):
            result=upload_source(SimpleUploadedFile('two.pdf',data.getvalue()),user.id)
            url=f'/sources/{result.source_id}/preview-image/'
            self.assertEqual(self.client.get(url).status_code,302)
            self.client.force_login(user)
            response=self.client.get(url+'?page=2')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['Content-Type'],'image/png')
            self.assertEqual(response['X-PDF-Page-Count'],'2')
            self.assertEqual(response['Cache-Control'],'private, no-store')
            self.assertLessEqual(max(Image.open(BytesIO(response.content)).size),1401)
            self.assertEqual(self.client.get(url+'?page=3').status_code,422)
            self.assertEqual(self.client.get(url+'?page=0').status_code,422)

import io, tempfile
from pathlib import Path
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook
from common.errors import ValidationError
from intake.models import SourceFile
from intake.services import upload_source

def excel_bytes():
    workbook=Workbook();ws=workbook.active
    ws.append(['고객명','테스트고객']);ws.append(['PO 번호','UPLOAD-1'])
    ws.append(['품목코드','품명','수량','단위','단가','통화','납기일'])
    ws.append(['PART-1','부품',100,'EA',0.2,'KRW','2026-10-19'])
    output=io.BytesIO();workbook.save(output);return output.getvalue()

class UploadTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('manager')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.override=override_settings(PRIVATE_MEDIA_ROOT=Path(self.tmp.name));self.override.enable();self.addCleanup(self.override.disable)
    def test_same_file_reuses_source(self):
        data=excel_bytes()
        a=upload_source(SimpleUploadedFile('a.xlsx',data),self.user.id)
        b=upload_source(SimpleUploadedFile('b.xlsx',data),self.user.id)
        self.assertEqual(a.source_id,b.source_id);self.assertEqual(SourceFile.objects.count(),1)
    def test_disguised_file_rejected(self):
        with self.assertRaises(ValidationError):upload_source(SimpleUploadedFile('bad.pdf',b'<html>not a PDF</html>'),self.user.id)
    def test_private_download_and_safe_path(self):
        result=upload_source(SimpleUploadedFile('../../unsafe.xlsx',excel_bytes()),self.user.id)
        source=SourceFile.objects.get(pk=result.source_id)
        self.assertTrue(Path(source.path).resolve().is_relative_to(Path(self.tmp.name).resolve()))
        self.assertEqual(self.client.get(f'/sources/{source.id}/download/').status_code,302)
        self.client.force_login(self.user)
        response=self.client.get(f'/sources/{source.id}/download/')
        self.assertEqual(response.status_code,200);self.assertEqual(b''.join(response.streaming_content),excel_bytes())

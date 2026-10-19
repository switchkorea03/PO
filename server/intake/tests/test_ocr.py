import io,tempfile,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from django.test import SimpleTestCase
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from intake.extractors.pdf import extract_pdf

class LocalOCRTests(SimpleTestCase):
    def test_scanned_pdf_text_is_read_locally(self):
        engine=os.getenv('TESSERACT_CMD')
        if not engine or not Path(engine).exists():self.skipTest('실제 로컬 Tesseract 엔진 미설치 · 운영 OCR 검수 필요')
        with tempfile.TemporaryDirectory() as directory:
            image=Image.new('RGB',(1800,900),'white');draw=ImageDraw.Draw(image)
            font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',50)
            draw.text((80,100),'PO No: SCAN-100',font=font,fill='black')
            draw.text((80,220),'Customer: Sample Company',font=font,fill='black')
            pdf=Path(directory)/'scan.pdf';c=canvas.Canvas(str(pdf),pagesize=(900,450));c.drawImage(ImageReader(image),0,0,width=900,height=450);c.save()
            result=extract_pdf(pdf)
            self.assertEqual(result.fields['po_number'].value,'SCAN-100')
            self.assertTrue(any(e.page==1 for e in result.evidence))

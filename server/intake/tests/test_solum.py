import tempfile
from pathlib import Path
from decimal import Decimal
from django.test import SimpleTestCase,TestCase
from django.contrib.auth import get_user_model
from intake.extractors.pdf import extract_pdf

def solum_pdf(path,*,rows=1,missing_quantity=False,foreign_buyer=False,scale=1,po='TEST-200'):
    from reportlab.pdfgen import canvas
    pdf=canvas.Canvas(str(path),pagesize=(600,850));pdf.scale(scale,scale);pdf.setFont('Helvetica',8)
    pdf.drawString(30,790,'PURCHASER ORDER (PO No.)'+po)
    pdf.drawString(30,760,'VENDOR : SAMPLE VENDOR DATE : 09/25/2026')
    pdf.drawString(300,745,'CURRENCY : USD')
    pdf.drawString(410,650,'(Company)'+('OTHER BUYER' if foreign_buyer else 'SOLU M VINA CO.,LTD'))
    for text,x,y in [('ITEM',45,370),('MATERIAL/VENDOR MATERIAL',85,380),('DESCRIPTION',85,369),('SPECIFICATION',85,358),('PRICE',250,370),('QUANTITY/',300,375),('UNIT',330,364),('AMOUNT',380,375),('OTHER CHARGE',355,364),('SHIPING',450,375),('INSTRUCTION',432,364),('DELIVERY',520,375),('[MM/DD/YYYY]',496,364)]:pdf.drawString(x,y,text)
    for i in range(rows):
        y=335-i*70
        pdf.drawString(52,y,str((i+1)*10));pdf.drawString(85,y,f'TEST-MAT-{i+1} /')
        pdf.drawString(224,y,'0.04150')
        if not missing_quantity:pdf.drawString(282,y+4,'1,080,000.0');pdf.drawString(322,y-5,'0')
        pdf.drawString(335,y,'PC');pdf.drawString(377,y,'44,820.00');pdf.drawString(450,y,'Vessel');pdf.drawString(515,y,f'10/{20+i:02d}/2026')
        pdf.drawString(85,y-17,'SWITCH-TACT;1,50mA,12V,3.');pdf.drawString(85,y-27,'95X2.9X1.65mm,100gf,TP,')
    pdf.drawString(360,335-rows*70,'TOTAL : 44,820.00')
    pdf.drawString(30,70,'Supplier terms and instructions must not become item rows.')
    pdf.save()

class SolumExtractionTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'sample.pdf'
    def test_wrapped_quantity_and_columns_preserve_exact_values(self):
        solum_pdf(self.path);result=extract_pdf(self.path)
        self.assertEqual(result.fields['po_number'].value,'TEST-200')
        self.assertEqual(result.fields['ordered_on'].value,'2026-09-25')
        self.assertEqual(result.fields['customer_name'].value,'솔루엠(베트남향)')
        self.assertEqual(result.fields['order_type'].value,'overseas')
        self.assertIsNone(result.fields['etd'].value)
        self.assertEqual(len(result.lines),1)
        line=result.lines[0]
        for key,value in {'code':'TEST-MAT-1','quantity':'1080000.00','unit':'PC','unit_price':'0.04150','currency':'USD','source_amount':'44820.00','requested_due':'2026-10-20'}.items():
            self.assertEqual(line[key].value,value,key)
        self.assertIn('3.95X2.9X1.65mm',line['name'].value)
        self.assertEqual(Decimal(line['quantity'].value)*Decimal(line['unit_price'].value),Decimal(line['source_amount'].value))
        self.assertTrue(line['quantity'].evidence)
    def test_multiple_rows_keep_their_dates_and_ignore_footer(self):
        solum_pdf(self.path,rows=2);result=extract_pdf(self.path)
        self.assertEqual([line['code'].value for line in result.lines],['TEST-MAT-1','TEST-MAT-2'])
        self.assertEqual([line['requested_due'].value for line in result.lines],['2026-10-20','2026-10-21'])
    def test_scaled_layout_uses_header_positions(self):
        solum_pdf(self.path,scale=.85);result=extract_pdf(self.path)
        self.assertEqual(result.lines[0]['quantity'].value,'1080000.00')
    def test_missing_quantity_is_not_inferred_from_amount(self):
        solum_pdf(self.path,missing_quantity=True);result=extract_pdf(self.path)
        self.assertEqual(len(result.lines),1)
        self.assertIsNone(result.lines[0]['quantity'].value)
    def test_other_buyer_does_not_match_solum_profile(self):
        solum_pdf(self.path,foreign_buyer=True);result=extract_pdf(self.path)
        self.assertIsNone(result.fields['customer_name'].value)

class SolumReviewTests(TestCase):
    def test_recognized_overseas_type_survives_missing_customer(self):
        from intake.models import SourceFile,ExtractionJob,ExtractionDraft
        user=get_user_model().objects.create_user('solum-manager');self.client.force_login(user)
        source=SourceFile.objects.create(sha256='a'*64,path='unused.pdf',original_name='sample.pdf',extension='.pdf',size=1,uploaded_by=user)
        job=ExtractionJob.objects.create(source=source,status='done')
        draft=ExtractionDraft.objects.create(job=job,result={'fields':{'customer_name':{'value':'솔루엠(베트남향)'},'order_type':{'value':'overseas'}},'lines':[]})
        response=self.client.get(f'/intake/{draft.id}/review/')
        self.assertEqual(response.context['initial_data']['order_type'],'overseas')
        self.assertEqual(response.context['initial_data']['customer_name'],'솔루엠(베트남향)')

from pathlib import Path
from decimal import Decimal
import tempfile
from django.test import SimpleTestCase
from intake.extractors.base import Evidence
from intake.extractors.mapping import map_evidence
from intake.extractors.pdf import extract_pdf


TEXT=[
 'Purchase Order','PO No 4600000001','PO Date 2026-10-13','Amount USD 11,353.20',
 'Buyer Detail','Representa CHEMTROVINA_Hochimin Plant','In Charge Pur TEST BUYER',
 'Supplier Detail','Representa (101151)Switch Korea Co., Ltd.',
 'No. Part No.','Descriptio','Spec','Design','Drawing(D','ocument)',
 'Quantity','Unit U/Price Amount Delivery By',
 '1 M01340001A DHT-1187AC;JT1140WJ-BEM;TACT;5*5*1.5;A','3404-001379','4,000.00','EA','0.01890 75.60 2027-01-04',
 '2 M01340002A JES1612GWAS;PUSH;17*15.4;A','JES1612GWAS','28,800.00','EA','0.14700 4,233.60 2026-11-30',
 '3 M01340003A JS1267EM;SLIDE;6.7*2.7*1.4;A','JS1267EM','69,000.00','EA','0.03720 2,566.80 2026-12-07',
 '4 M01340016A SKRWAEE030;TACT;3.7**3.7*0.35;A','SKRWAEE030','300,000.00','EA','0.01396 4,188.00 2026-12-14',
 '5 M01340028A JS6901; Slide Switch','JS6901; Slide Switch','4,000.00','EA','0.07230 289.20 2026-12-21',
 'USD Total Amount 11,353.20',' /']


class ChemtrovinaExtractionTests(SimpleTestCase):
    def parse(self,text=TEXT):
        return map_evidence(tuple(Evidence(1,None,None,line) for line in text))

    def assert_result(self,result):
        self.assertEqual(result.fields['po_number'].value,'4600000001')
        self.assertEqual(result.fields['ordered_on'].value,'2026-10-13')
        self.assertEqual(result.fields['customer_name'].value,'켐트로비나')
        self.assertEqual(result.fields['order_type'].value,'overseas')
        self.assertEqual(result.fields['contact'].value,'Pur TEST BUYER')
        self.assertEqual(len(result.lines),5)
        first=result.lines[0]
        self.assertEqual(first['code'].value,'M01340001A')
        self.assertIn('3404-001379',first['name'].value)
        self.assertEqual(Decimal(first['quantity'].value),4000)
        self.assertEqual(first['unit'].value,'EA')
        self.assertEqual(first['unit_price'].value,'0.01890')
        self.assertEqual(first['currency'].value,'USD')
        self.assertEqual(first['requested_due'].value,'2027-01-04')
        self.assertEqual(sum(Decimal(line['source_amount'].value) for line in result.lines),Decimal('11353.20'))

    def test_colonless_header_and_wrapped_items(self):
        self.assert_result(self.parse())

    def test_real_pdf_text_pipeline(self):
        from reportlab.pdfgen import canvas
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'chemtrovina.pdf';pdf=canvas.Canvas(str(path),pagesize=(600,850));pdf.setFont('Helvetica',9)
            for index,text in enumerate(TEXT):pdf.drawString(25,825-index*13,text)
            pdf.save();self.assert_result(extract_pdf(path))

    def test_incomplete_item_is_flagged_instead_of_assigned_wrong_values(self):
        result=self.parse([line for line in TEXT if line!='0.01890 75.60 2027-01-04'])
        self.assertEqual(len(result.lines),5)
        self.assertIsNone(result.lines[0]['quantity'].value)
        self.assertIsNone(result.lines[0]['requested_due'].value)
        self.assertTrue(any('미인식' in warning for warning in result.warnings))

    def test_supplier_is_not_mistaken_for_buyer(self):
        text=[line.replace('CHEMTROVINA_Hochimin Plant','OTHER BUYER').replace('(101151)Switch Korea Co., Ltd.','CHEMTROVINA') for line in TEXT]
        result=self.parse(text)
        self.assertNotEqual(result.fields['customer_name'].value,'켐트로비나')

from django.test import SimpleTestCase
from intake.extractors.base import Evidence
from intake.extractors.mapping import map_evidence

class BumjinFormatTests(SimpleTestCase):
    def extract(self,rows):
        return map_evidence(tuple(Evidence(1,None,None,row) for row in rows))

    def header(self):
        return ['Purchase Order','PO no. TEST-100','Po Date 2026.08.19','Charger 구매-테스트',
                'Buyer Vendor','BUMJIN ELECTRONICS CO.,LTD SAMPLE VENDOR',
                'CUR USD','End Customer BUMJIN ELECTRONICS VINA CO.LTD',
                'Item Material Old material Material Description Quantity Unit Price Amount',
                'Customer code Specification Delivery Date']

    def test_two_level_header_and_multiline_specification_and_due(self):
        result=self.extract(self.header()+['00010 PART-001 SWITCH-TACT DIP 40,000 EA 0.0145 580.00',
             'MODEL-A,SW','TACT,160gf,6.2x6.2x5','2027.01.05','Total Items. 1 Total Amount. 580.00'])
        self.assertEqual(result.fields['po_number'].value,'TEST-100')
        self.assertEqual(result.fields['ordered_on'].value,'2026-08-19')
        self.assertEqual(result.fields['customer_name'].value,'범진전자')
        self.assertEqual(result.fields['contact'].value,'구매-테스트')
        self.assertEqual(len(result.lines),1)
        line=result.lines[0]
        for key,value in {'code':'PART-001','quantity':'40000','unit':'EA','unit_price':'0.0145','currency':'USD','source_amount':'580.00','requested_due':'2027-01-05'}.items():
            self.assertEqual(line[key].value,value,key)
        self.assertIn('MODEL-A,SW',line['name'].value)
        self.assertEqual(line['requested_due'].evidence[0].text,'2027.01.05')

    def test_separate_rows_keep_their_own_due_and_ignore_footer(self):
        result=self.extract(self.header()+['00010 PART-A Part A 10 EA 1.25 12.50','2027.01.05',
             '00020 PART-B Part B 20 EA 2.50 50.00','2027.02.02','Total Items. 2 Total Amount. 62.50',
             '00030 FAKE-1 Footer text 999 EA 1.00 999.00'])
        self.assertEqual(len(result.lines),2)
        self.assertEqual([line['requested_due'].value for line in result.lines],['2027-01-05','2027-02-02'])

    def test_missing_due_is_left_empty_for_review(self):
        result=self.extract(self.header()+['00010 PART-A Part A 10 EA 1.25 12.50','Total Items. 1 Total Amount. 12.50'])
        self.assertEqual(len(result.lines),1)
        self.assertIsNone(result.lines[0]['requested_due'].value)

    def test_same_row_shape_without_table_headers_is_not_a_po_line(self):
        result=self.extract(['00010 PART-A Part A 10 EA 1.25 12.50','2027.01.05'])
        self.assertEqual(len(result.lines),0)

    def test_pdf_reader_retains_multiline_table_values(self):
        import tempfile
        from pathlib import Path
        from reportlab.pdfgen import canvas
        from intake.extractors.pdf import extract_pdf
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sample.pdf';pdf=canvas.Canvas(str(path))
            rows=self.header()+['00010 PART-001 SWITCH-TACT DIP 40,000 EA 0.0145 580.00','MODEL-A,SW','2027.01.05','Total Items. 1 Total Amount. 580.00']
            for index,text in enumerate(rows):pdf.drawString(15,800-index*18,text)
            pdf.save();result=extract_pdf(path)
        self.assertEqual(result.lines[0]['quantity'].value,'40000')
        self.assertEqual(result.lines[0]['requested_due'].value,'2027-01-05')

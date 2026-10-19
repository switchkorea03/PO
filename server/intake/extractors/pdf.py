import os
from .base import Evidence
from .mapping import map_evidence

def extract_pdf(path):
    import pypdfium2 as pdfium
    document=pdfium.PdfDocument(str(path));evidence=[]
    try:
        if len(document)>100:raise ValueError('PDF 100페이지 제한 초과 · 직접 입력하세요.')
        for index in range(len(document)):
            page=document[index];textpage=page.get_textpage()
            try:text=textpage.get_text_range()
            finally:textpage.close()
            if not text.strip():
                import pytesseract
                command=os.getenv('TESSERACT_CMD')
                if command:pytesseract.pytesseract.tesseract_cmd=command
                bitmap=page.render(scale=2)
                try:text=pytesseract.image_to_string(bitmap.to_pil(),lang='kor+eng',timeout=100)
                finally:bitmap.close()
            for line in text.splitlines():
                if line.strip():evidence.append(Evidence(index+1,None,None,line))
            page.close()
    finally:document.close()
    return map_evidence(tuple(evidence))

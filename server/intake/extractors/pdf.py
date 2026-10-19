import os
from .base import Evidence
from .mapping import map_evidence

def extract_pdf(path):
    import pypdfium2 as pdfium
    from .solum import extract_page,combine
    document=pdfium.PdfDocument(str(path));evidence=[];solum_pages=[]
    try:
        if len(document)>100:raise ValueError('PDF 100페이지 제한 초과 · 직접 입력하세요.')
        for index in range(len(document)):
            page=document[index];textpage=page.get_textpage()
            try:
                text=textpage.get_text_range()
                profile=extract_page(textpage,index+1,page.get_width(),known=bool(solum_pages))
                if profile is not None:solum_pages.append(profile)
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
    return combine(solum_pages,tuple(evidence)) if solum_pages else map_evidence(tuple(evidence))

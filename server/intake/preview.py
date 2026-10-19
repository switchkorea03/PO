"""Bounded local PDF rendering; serialize PDFium calls inside the web process."""
from io import BytesIO
from math import isfinite
from threading import Lock
from common.errors import ValidationError

_render_lock=Lock()

def render_page(path,number):
    import pypdfium2 as pdfium
    with _render_lock:
        try:
            with pdfium.PdfDocument(str(path)) as document:
                count=len(document)
                if not 0<count<=100 or not 1<=number<=count:raise ValidationError('PDF 페이지 범위를 확인하세요.')
                page=document[number-1]
                try:
                    width,height=page.get_size()
                    if not all(isfinite(v) and v>0 for v in (width,height)):raise ValidationError('PDF 페이지 크기를 확인하세요.')
                    scale=min(1.5,1400/max(width,height))
                    bitmap=page.render(scale=scale)
                    try:
                        output=BytesIO();bitmap.to_pil().save(output,format='PNG')
                        return output.getvalue(),count
                    finally:bitmap.close()
                finally:page.close()
        except ValidationError:raise
        except Exception as exc:
            raise ValidationError('PDF 미리보기를 생성하지 못했습니다. 원본을 다운로드하여 확인하세요.') from exc

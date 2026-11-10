"""Local PNG OCR with no external file transmission."""
import os
from PIL import Image
import pytesseract
from .base import Evidence
from .mapping import map_evidence

def extract_image(path):
    command=os.getenv('TESSERACT_CMD')
    if command:pytesseract.pytesseract.tesseract_cmd=command
    with Image.open(path) as source:
        if source.format!='PNG' or source.width*source.height>25_000_000:
            raise ValueError('지원하는 PNG 크기를 확인하세요.')
        rgba=source.convert('RGBA')
        image=Image.new('RGB',rgba.size,'white');image.paste(rgba,mask=rgba.getchannel('A'))
        try:text=pytesseract.image_to_string(image,lang='kor+eng',timeout=100)
        finally:image.close();rgba.close()
    return map_evidence(tuple(Evidence(1,None,None,line) for line in text.splitlines() if line.strip()))

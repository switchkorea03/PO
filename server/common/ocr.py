"""Resolve local OCR binaries/models, including Windows non-ASCII workspaces."""
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

def configure_local_ocr(bundle):
    configured=Path(os.getenv('TESSERACT_CMD','missing'))
    root=configured.parent if configured.is_file() else Path(bundle)
    engine=root/'tesseract.exe'
    if not engine.is_file():return
    data=Path(os.getenv('TESSDATA_PREFIX','missing'))
    if not (data/'eng.traineddata').is_file() or not (data/'kor.traineddata').is_file():data=root/'tessdata'
    if not (data/'eng.traineddata').is_file() or not (data/'kor.traineddata').is_file():return
    if os.name=='nt' and (not str(root).isascii() or not str(data).isascii()):
        # Tesseract's Windows filesystem implementation rejects Unicode model
        # paths. Copy only the already installed runtime into a local ASCII cache.
        token=hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:12]
        cache=Path(tempfile.gettempdir())/f'po-desk-ocr-{token}'
        if not str(cache).isascii() or cache.is_symlink():raise RuntimeError('OCR용 영문 경로를 설정하세요.')
        cache.mkdir(exist_ok=True)
        model_cache=cache/'tessdata'
        if model_cache.is_symlink():raise RuntimeError('OCR 모델 캐시 경로를 확인하세요.')
        model_cache.mkdir(exist_ok=True)
        pairs=[(engine,cache/'tesseract.exe')]+[(path,cache/path.name) for path in root.glob('*.dll')]
        pairs += [(data/f'{lang}.traineddata',model_cache/f'{lang}.traineddata') for lang in ('eng','kor')]
        for source,target in pairs:
            if target.is_symlink():raise RuntimeError('OCR 캐시 파일 경로를 확인하세요.')
            if not target.exists() or source.stat().st_size!=target.stat().st_size or source.stat().st_mtime_ns>target.stat().st_mtime_ns:
                shutil.copy2(source,target)
        engine=cache/'tesseract.exe';data=model_cache
    os.environ['TESSERACT_CMD']=str(engine)
    os.environ['TESSDATA_PREFIX']=str(data)

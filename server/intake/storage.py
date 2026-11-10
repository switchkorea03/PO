import hashlib,uuid,zipfile,io
from pathlib import Path
from django.conf import settings
from common.errors import ValidationError

MAX_SIZE=20*1024*1024
def validate_upload(file):
    if file.size>MAX_SIZE:raise ValidationError('파일이 20MiB를 초과합니다. 분리하거나 직접 입력하세요.')
    extension=Path(file.name).suffix.lower()
    content=file.read(MAX_SIZE+1)
    if len(content)>MAX_SIZE:raise ValidationError('파일 크기 제한을 초과합니다.')
    valid=False
    if extension=='.pdf':valid=content.startswith(b'%PDF-')
    elif extension=='.png':
        try:
            import warnings
            from PIL import Image
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    valid=image.format=='PNG' and image.width*image.height<=25_000_000
                    image.verify()
        except Exception:valid=False
    elif extension=='.xls':valid=content.startswith(bytes.fromhex('D0CF11E0A1B11AE1'))
    elif extension=='.xlsx' and content.startswith(b'PK'):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                infos=archive.infolist()
                valid='xl/workbook.xml' in archive.namelist() and sum(i.file_size for i in infos)<=100*1024*1024 and len(infos)<2000
        except zipfile.BadZipFile:pass
    if not valid:raise ValidationError('실제 PDF·PNG·xlsx·xls 형식을 확인하세요. PNG는 2,500만 화소 이하를 지원합니다.')
    return extension,content,hashlib.sha256(content).hexdigest()

def write_private(content,extension):
    root=Path(settings.PRIVATE_MEDIA_ROOT).resolve();root.mkdir(parents=True,exist_ok=True)
    path=root/(str(uuid.uuid4())+extension)
    with path.open('xb') as stream:stream.write(content)
    return path

import sys,json
from pathlib import Path
from dataclasses import asdict
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from intake.extractors.pdf import extract_pdf
from intake.extractors.excel import extract_excel
from intake.extractors.image import extract_image
if __name__=='__main__':
    try:
        path=Path(sys.argv[1]);extension=sys.argv[2]
        result=extract_pdf(path) if extension=='.pdf' else extract_image(path) if extension=='.png' else extract_excel(path,extension)
        sys.stdout.reconfigure(encoding='utf-8')
        print(json.dumps(asdict(result),ensure_ascii=False))
    except Exception as exc:
        sys.stderr.reconfigure(encoding='utf-8');print(f'{type(exc).__name__}: {exc}',file=sys.stderr);sys.exit(1)

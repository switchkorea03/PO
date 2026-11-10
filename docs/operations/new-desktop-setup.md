# 다른 Windows 데스크탑에서 이어서 개발하기

저장소: https://github.com/switchkorea03/PO

기존 노트북의 작업 폴더를 그대로 덮어쓰지 않고, 새 PC의 별도 폴더에 내려받습니다. 이 저장소에는 소스·설계·마이그레이션·테스트·실행 스크립트가 들어 있습니다. 고객 PO 원본, DB 데이터, `.env` 인증정보, 설치된 실행 프로그램은 포함하지 않습니다.

## 1. 소스와 Python 환경

Python 3.12, Git, PostgreSQL 17, Tesseract 5(eng/kor 언어 모델)를 준비합니다. 브라우저 테스트를 할 경우 Node.js와 Playwright도 준비합니다.

```powershell
git clone https://github.com/switchkorea03/PO.git
cd PO
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r server/requirements.lock
```

테스트 의존성은 다음과 같이 추가합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r server/requirements-dev.in
```

## 2. 새 PC의 데이터베이스와 비공개 설정

PostgreSQL에 웹앱용 로그인 계정과 `po_calendar` DB를 만들고 해당 계정이 그 DB를 사용할 수 있게 설정합니다. 아래 예시 파일을 복사한 뒤 실제 연결정보를 직접 입력합니다. 이미 `.env`가 있으면 덮어쓰지 않습니다.

```powershell
if (-not (Test-Path server/.env)) { Copy-Item server/.env.example server/.env }
```

확인할 설정:

- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`: 새 PC의 실제 PostgreSQL 접속값. 일반 설치의 기본 포트는5432이며, 기존 노트북 포터블 DB는55432를 사용했습니다.
- `SECRET_KEY`: 새 PC에서 생성한 비공개 값. 기존 파일의 샘플 문자열을 운영용으로 사용하지 않습니다.
- `TESSERACT_CMD`, `TESSDATA_PREFIX`: 새 PC에 설치한 Tesseract 실행 파일과 kor/eng 모델 폴더의 실제 위치. 예: `C:/Program Files/Tesseract-OCR/tesseract.exe`, `C:/Program Files/Tesseract-OCR/tessdata`.
- `PRIVATE_MEDIA_ROOT`: 원본 보관 위치. 생략하면 `server/private_media`입니다.
- `SMS_PROVIDER=unconfigured`, `SMS_LIVE_ENABLED=0`: 실제 발송을 준비하기 전까지 유지합니다.
- `GEMINI_API_KEY`: 회사에서 사용할 인증정보가 있을 때만 비공개로 설정합니다. 키가 없어도 로컬 인식과 직접 등록은 사용할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe server/manage.py migrate --noinput
.\.venv\Scripts\python.exe server/manage.py check
```

완전히 새 DB로 시작할 때만 관리자와 기본 고객을 생성합니다. 기존 DB를 복원한 경우 기존 계정을 사용합니다.

```powershell
.\.venv\Scripts\python.exe server/manage.py createsuperuser
.\.venv\Scripts\python.exe server/manage.py seed_po_defaults
```

## 3. 실제 웹앱과 인식 worker 실행

아래는 새 PC에서 일반 설치 PostgreSQL을 사용할 때의 실행 방법입니다. PowerShell 창을 각각 열고 저장소 루트에서 실행합니다.

웹 서버:

```powershell
Push-Location server
..\.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:8000 config.wsgi:application
Pop-Location
```

파일 인식 worker:

```powershell
.\.venv\Scripts\python.exe server/manage.py run_intake_worker
```

실제 웹앱: http://127.0.0.1:8000/

목업이 필요한 경우에만 별도 창에서 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m http.server 4174 --bind 127.0.0.1 --directory ui-prototype/dist
```

목업: http://127.0.0.1:4174/ — 예시 데이터이며 실제 PO DB를 사용하지 않습니다.

`ops/start-local.ps1`과 자동 시작 등록은 기존 노트북의 `.runtime/postgresql/pgsql`, `.runtime/pgdata` 포터블 배치를 전제로 합니다. 새 PC에서 일반 설치 PostgreSQL을 쓴다면 위 수동 실행으로 먼저 확인한 뒤, 실제 환경에 맞게 자동 시작을 설정합니다. 저장소만 내려받으면 `.runtime`이 자동 설치되는 것은 아닙니다.

## 4. 기존 업무 데이터까지 이전하려면

소스 다운로드와 데이터 복원은 별개입니다. 기존 PC에서 DB와 PO 원본을 함께 비공개 백업하고, 새 PC의 **새 복구 DB·새 원본 폴더**에 복원·검증한 다음 연결합니다. 백업에는 고객 정보가 포함되므로 GitHub에 커밋하지 않습니다.

- [백업·복구 절차](backup-restore.md)
- [실행 환경·배포](deployment.md)

문자 수신번호, 관리자 계정과 기존 PO는 DB에 있으므로 새 빈 DB에는 나타나지 않습니다. `.env`의 API 키·DB 비밀번호도 별도 비공개 설정이 필요합니다.

## 5. ERP 연동을 이어갈 위치

- [데스크탑 ERP 인계 문서](2026-11-09-desktop-erp-handoff.md)
- `server/inventory/providers.py`: 현재는 ERP 미연결 공급자입니다. 실제 iCUBE의 승인된 조회 경로를 확인하고 공급자를 구현할 위치입니다.
- `server/inventory/queries.py`, `views.py`, `templates/inventory/`: 재고 조회 화면과 PO 미출고 집계입니다.
- `server/orders/item_mapping.py`: 고객품목·자사품목 연결을 확인할 위치입니다.

ERP의 API 주소·DB 테이블·로그인 정보는 아직 정해지지 않았습니다. 실제 ERP 조회가 연결되기 전에는 재고를0으로 채우거나 연결 완료로 표시하지 않습니다.

## 6. 검증과 다음 수정

```powershell
.\.venv\Scripts\python.exe server/manage.py test orders work accounts intake notices inventory common.tests --noinput -v 1
.\.venv\Scripts\python.exe server/manage.py makemigrations --check --dry-run
node --test ui-prototype/tests/rules.test.mjs server/e2e/numbers.test.mjs
```

브라우저 테스트는 `server/e2e`에서 `npm.cmd ci`, `npx.cmd playwright install chromium` 후 실행합니다. E2E는 별도 테스트 DB를 초기화하므로 테스트 DB 설정·DB 생성 권한을 확인합니다. DB 백업 검증에는 PostgreSQL의 `pg_dump`·`pg_restore` 위치(`PG_BIN`), OCR 검증에는 Tesseract kor/eng가 필요합니다.

다른 PC의 Codex에서 이어갈 때는 이 문서와 ERP 인계 문서를 먼저 읽도록 요청하고, 실제 ERP 버전·회사/사업장·조회 권한·창고/품목코드/단위 정보를 전달하면 됩니다.

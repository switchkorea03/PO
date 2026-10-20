# PO 관리 · 업무 달력

실제 PostgreSQL 저장을 사용하는 사내 웹 서비스입니다. 기존 `po-calendar/`, `ui-mockup/` 목업은 그대로 보존했습니다.

## 현재 컴퓨터에서 실행

작업 폴더 `D:\Documents\ChatGPT\PO자동화`의 PowerShell에서 실행합니다.

```powershell
.\ops\start-local.ps1
```

- 주소: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- 최초 로컬 로그인 정보: 작업 폴더의 `.runtime/local-login.txt`.
- 웹 서버만 앞에서 실행하려면 `.\ops\start-web.ps1`, 파일 인식 worker는 `.\ops\start-workers.ps1`을 사용합니다.
- DB는 포트55432, 테스트 웹은8001을 사용합니다. 기존8000 서버가 있으면 중복 실행하지 않습니다.
- 로컬 바이너리·DB·비공개 설정은 작업 폴더 `.runtime/`, `.venv/`, `server/.env`에 있습니다. Git에는 포함하지 않습니다.
- 한국어 경로 호환 때문에 `P:`를 `.runtime/`에 매핑합니다. 다른 용도의 P:가 있으면 시작을 중단하며 덮어쓰지 않습니다.

현재 PC는 Windows 로그인 시 실제 웹앱·파일 인식·목업을 자동 실행하도록 등록했습니다. 재등록·해제와 실행 기록은 [자동 실행 안내](../docs/operations/autostart.md)를 참고하세요. 메뉴 위치·화면 디자인도 실제 웹앱에서 계속 수정할 수 있으며, 목업은 큰 화면 변경을 미리 검토할 때 사용합니다.

## 구현 범위

로그인·계정 권한, 고객·다품목 PO, 납기별 초기 회차, 분할출고·실적·잔량·취소·정정, 국내외 날짜 계산, 월간·주간 달력, 수동 날짜 이동, 세부 작업 체크·재확인·이력, 원본 보관·PDF/Excel/스캔 인식·등록 확인, 문자 정기·추가 알림·재시도·복구를 포함합니다.

ERP·메일·공유 Excel은 직접 처리합니다. 인보이스 번호·파일·PO 연결은 관리하지 않습니다. 납기는 국내만 달력에 표시하며 해외 원문 납기는 계산에 쓰지 않습니다.

## 문자 연결

현재 실제 문자 발송은 비활성입니다. SOLAPI 어댑터를 구현했으나 계정·요금제·서비스 사용 계약을 생성하지 않았습니다. 회사에서 사용할 서비스를 확정한 후 아래를 비공개 `.env`에 설정합니다.

```dotenv
SMS_PROVIDER=solapi
SMS_LIVE_ENABLED=1
SMS_API_KEY=본인의_API_키
SMS_API_SECRET=본인의_API_시크릿
```

화면에서 본인 수신번호·사전 등록한 발신번호를 저장하고 알림 사용을 선택한 다음 문자 worker를 재시작합니다. 인증정보를 MD 파일이나 Git에 기록하지 않습니다. 다른 공급자는 `notices/providers/base.py` 계약에 맞는 어댑터로 교체합니다.

- 평일09시 KST: 오늘 + 이전 미완료 업무. 새 당일 업무는 추가 알림.
- 분할 문자 중 일부만 접수되면 접수된 부분을 다시 보내지 않습니다.
- 일부 접수 후 내용이 바뀌면 나머지 문자 전송을 멈추고 이력에 확인 필요를 표시합니다.
- timeout은 실패로 단정하지 않고 공급자 내역을 조회합니다. 조회로도 확정하지 못하면 자동 재발송하지 않습니다.
- 로컬 개발에서만 `SMS_PROVIDER=fake`로 실제 발송 없는 테스트가 가능합니다.

## 테스트

```powershell
.\.venv\Scripts\python.exe server/manage.py test orders work accounts intake notices common.tests -v 2 --noinput
cd server/e2e
npm ci
npx playwright test
```

E2E는 별도 `po_calendar_e2e` DB를 초기화합니다. 일반 DB나 실제 문자 공급자를 사용하지 않습니다. OCR 통합 테스트는 로컬 엔진·kor/eng 모델을 실제로 호출합니다. 실제 고객 PO별 인식 품질과 실제 휴대폰 수신은 별도 인수 대상입니다.

## 다른 컴퓨터 환경 준비

Python3.12 가상환경에서 `pip install --require-hashes -r server/requirements.lock`을 실행합니다. PostgreSQL17, Tesseract5와 kor/eng 모델을 회사 승인 경로에 설치합니다. `server/.env.example`을 비공개 `.env`로 복사해 DB·원본 보관 경로·보안키를 지정하고 migrate, createsuperuser를 실행합니다. Windows 로컬 스크립트는 현재 작업 폴더의 포터블 경로를 전제로 하므로 운영 배포는 아래 문서를 따릅니다.

## 운영 문서

- [배포](../docs/operations/deployment.md)
- [백업·복구](../docs/operations/backup-restore.md)
- [인수·검증 결과](../docs/operations/acceptance.md)

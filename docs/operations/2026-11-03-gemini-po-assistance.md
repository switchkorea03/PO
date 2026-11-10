# Gemini PO 인식·검증 보조 연결

2026-11-03, 로컬 웹앱 http://127.0.0.1:8000/ 기준.

## 사용 순서

1. 기존처럼 PO 파일을 업로드하고 로컬 인식 결과 확인 화면으로 이동합니다.
2. `Gemini로 인식·검증 보완`에서 Google 전송에 동의하고 `Gemini로 인식 보완`을 누릅니다.
3. AI 제안의 고객·PO번호·품목·수량·단가·공급가액·납기를 원본과 비교합니다.
4. `AI 제안 적용`을 누르면 초안만 바뀝니다. 현재 편집 중인 내용은 교체됩니다.
5. 내용을 수정·확인하고 기존 `PO 저장`으로 등록합니다.

기존 PO 수령일과 URL로 선택한 수정 대상은 적용 후에도 유지됩니다. 오류·한도 초과 시 기존 초안은 유지되며 자동 재시도하지 않습니다. 분석만으로 PO나 업무를 생성하지 않습니다.

## 서버 설정

키는 Git에서 제외한 `server/.env`의 `GEMINI_API_KEY`에만 저장합니다. 브라우저로 키를 전달하지 않으며 요청 URL에도 포함하지 않습니다. 모델은 `GEMINI_MODEL=gemini-3.1-flash-lite`, 앱 공통 실행 제한은 `GEMINI_DAILY_LIMIT=20`입니다. 설정 변경 후 웹 서버를 재시작합니다.

앱 제한은 한국 시간 하루 기준이며 실패한 시도도 포함합니다. Google의 프로젝트별 RPM·TPM·RPD와는 별도입니다. 정확한 프로젝트 한도는 [AI Studio](https://aistudio.google.com/rate-limit?timeRange=last-28-days)에서 확인합니다. Google RPD는 태평양 시간 자정 기준입니다.

AI 보완은 파일당 최대 10MiB, 품목 최대 200개입니다. 기존 로컬 업로드 한도 20MiB는 유지합니다. PDF·PNG는 원본을, Excel은 로컬에서 추출한 셀 내용을 전송합니다. Excel 셀 근거가 200,000자를 초과하면 나누어서 처리합니다. 출력이 잘리면 부분 적용하지 않습니다.

무료 API의 입력·출력은 Google 제품 개선에 사용될 수 있으므로 전송 동의 화면에 이를 표시했습니다. [공식 요금 안내](https://aistudio.google.com/docs/pricing#gemini-3.1-flash-lite), [공식 한도 안내](https://aistudio.google.com/docs/rate-limits).

## 데이터 및 검증

- `GeminiReview`: 원본 초안 사본, AI 제안, 모델, 사용 토큰, 실행·적용 상태를 보관합니다.
- `GeminiDailyUsage`: 앱의 날짜별 실행 횟수를 보관하며 DB 잠금으로 동시 요청을 제한합니다.
- DB 변경 전 백업: `.runtime/backups/2026-11-03-before-gemini/`.
- 인증 확인 및 실제 Gemini 가상 PDF 인식 성공: PO번호, 수량, 자사품목명 매핑, 납기일 검증. 해당 요청 966토큰. 실제 업무 파일은 외부 테스트에 사용하지 않았습니다.
- 브라우저 통합 검증은 별도 `po_calendar_e2e` DB와 `serve_gemini.py`의 로컬 Gemini 모형으로 수행합니다. 운영 DB에 테스트 PO를 등록하지 않습니다.
- 응답 스키마의 `maxItems=200`은 Google에서 복잡도 오류를 유발하여 제거했습니다. 서버의 200품목 검증과 프롬프트 제한은 유지합니다.
- 최종 서버 테스트 140개, PC·모바일 브라우저 통합 테스트 6개 통과. Django 시스템 검사 정상, 미반영 모델 변경 없음. 실제 8000번 서버 재시작 후 로그인·Gemini 정적 스크립트 HTTP 200 확인.

검증 명령:

```powershell
.\.venv\Scripts\python.exe server/manage.py test orders work accounts intake notices common.tests --noinput -v 1
.\.venv\Scripts\python.exe server/manage.py check
.\.venv\Scripts\python.exe server/manage.py makemigrations --check --dry-run
```

브라우저 모형 서버는 운영 서버와 별도로 시작합니다. 이 명령은 테스트 DB를 초기화합니다.

```powershell
.\.venv\Scripts\python.exe server/e2e/serve_gemini.py
```

다른 터미널에서 `server/e2e`로 이동한 뒤:

```powershell
npx playwright test gemini.spec.mjs chemtrovina.spec.mjs spec-bulk.spec.mjs --config=requested-changes.config.mjs --project=desktop --project=mobile
```

# PDF 업로드 없는 프론트엔드·백엔드·DB 연동 검증

검증일: 2026-10-23 (한국시간)

## 결과

국내·해외 각 1개 시나리오를 PC(1440×1000)와 모바일(360×800)에서 실행하여 **4개 통과, 실패 0개, 건너뜀 0개**를 확인했습니다. 최종 테스트 명령 종료 코드는 0이며 실행 시간은 약 65초입니다.

## 환경과 방법

- 실제 Django 앱의 템플릿·JavaScript·API·모델을 그대로 사용하는 전용 서버: `http://127.0.0.1:8001/`.
- 실제 PostgreSQL 테스트 데이터베이스: `po_calendar_e2e`. 운영용 DB와 분리했습니다.
- 파일 업로드 대신 `/orders/new/` 화면에서 가상 고객과 PO를 직접 등록했습니다.
- Playwright가 화면의 입력·저장·조회·완료 버튼을 조작했습니다. DB나 내부 서비스를 직접 호출하여 테스트 PO를 생성하지 않았습니다.
- 별도 Python 프로세스가 Django ORM으로 저장값을 읽고 `SELECT current_database()`로 실제 연결 DB를 확인했습니다.
- 화면·DB 값을 교차 검증했습니다. 업로드 파일과 연결 원본 수는 모두 0이었습니다. 실제 문자 발송은 비활성화한 fake 설정입니다.

## 검증 항목

| 항목 | 확인 결과 |
|---|---|
| 국내 PO 등록 | 주문수량 100, 단가 1,500, 공급가액 150,000이 DB에 저장됨 |
| 국내 일정 생성 | 10/29 출고 기준 10/28 공유 업무 등 업무 5개 생성 |
| 초과 배정 차단 | 주문 100에 배정 101 입력 시 HTTP 422와 오류 문구 표시; 실적 변경 없음 |
| 분할출고 | 70/30 회차 생성 후 1차 완료 → 출고 70, 잔량 30 |
| 새로고침 | 출고·잔량과 저장 날짜가 유지됨 |
| 업무 완료 | 달력에서 공유 업무 체크 → DB 업무 상태 done, 완료 세부 작업 1개, 감사 이력 저장 |
| 해외 PO 등록 | 주문수량 100, 단가 USD 12.5, 공급가액 USD 1,250 저장 |
| 해외 수령일 | 10/23 수령 → 당일 업무 10/23, 다음 주 화요일 업무 10/27 |
| ETD 미정 | 후속 업무 3개 날짜 미정·보류 |
| 해외 선적 날짜 | ETD 10/31(토), ETA 11/04 입력 → 현재 최종 설계의 ETD+1 평일 보정에 따라 후속 업무 11/02(월) |
| PO 수정 재계산 | 수령일을 10/26으로 수정 → 다음 주 화요일 업무 11/03으로 이동 |
| 파일 업로드 생략 | 연결 원본 및 업로드 파일 수 0 |
| 브라우저 오류 | 각 시나리오의 미처리 JavaScript 오류 0 |

## 저장한 검증 코드와 증거

- `server/e2e/no-upload.spec.mjs`: 화면 기반 국내·해외 통합 테스트.
- `server/e2e/db_snapshot.py`: 테스트 DB 전용 읽기 검증 도구. 일반 업무 DB에서는 실행하지 않도록 DB명 검사 포함.
- `server/e2e/no-upload.reuse.config.mjs`: 이미 실행 중인 전용 테스트 서버를 재사용하는 설정.
- `.runtime/no-upload-report.json`: 최종 Playwright 결과와 단계별 DB 조회 JSON 첨부.
- `.runtime/no-upload-final.log`: 최종 4개 통과 로그.
- `.runtime/no-upload-domestic-desktop.png`, `.runtime/no-upload-overseas-desktop.png`: 실제 화면 캡처. 모바일 캡처도 같은 파일명의 mobile 버전으로 저장.

## 다시 실행

기본 설정은 테스트 DB를 초기화하므로 일반 업무 DB에는 사용하지 않습니다.

```powershell
cd server/e2e
npx.cmd playwright test no-upload.spec.mjs --project=desktop --project=mobile
```

Windows에서 자동 생성된 테스트 서버의 종료 단계가 대기하는 현상이 관찰되었습니다. 기능 검증과 서버 종료를 분리하기 위해 이미 실행 중인 `server/e2e/serve.py` 서버에 연결하여 다음 명령으로 재검증했고 정상 종료·JSON 보고서 생성을 확인했습니다.

```powershell
npx.cmd playwright test --config=no-upload.reuse.config.mjs --project=desktop --project=mobile
```

일반 업무 앱 코드와 데이터를 변경하지 않았습니다. 가상 고객·PO는 테스트 DB에만 생성했습니다. 이번 검증에는 PDF/Excel 인식 품질과 실제 문자 수신은 포함하지 않았습니다.

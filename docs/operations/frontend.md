# 실제 웹앱 프론트엔드

최종 설계 기반 `ui-prototype/` 목업의 화면 구성을 실제 Django 웹앱(8000번 포트)에 반영했습니다. 4174번 목업은 화면 검토용으로 별도 유지합니다.

## 화면과 연결

| 화면 | 실제 경로 | 연결된 기능 |
|---|---|---|
| 업무 달력 | `/calendar/` | 실제 업무, 상태·고객·국내외 필터, 월간·주간, 날짜 선택 |
| 현황 카드 | 달력·PO 목록 | 오늘·지연 업무, 잔량 있는 PO, ETD 미정 회차 |
| PO 목록·상세 | `/orders/` | 실제 품목·금액·잔량·회차·실적·취소·정정·원본·이력 |
| 직접 등록·수정 | `/orders/new/` | 다품목 입력, 기존 고객 재사용, 품목 추가·삭제 |
| 업로드 | `/intake/upload/` | 실제 PDF/Excel 업로드, 파일명·크기, 드래그 입력 |
| 인식값 확인 | `/intake/<draft>/review/` | 실제 원본 PDF 페이지 이미지와 추출값 비교, 수정본 연결 |
| 업무 상세 | `/tasks/<task>/` | 세부 작업 체크, 수동 날짜·자동 복원, 완료 후 재확인 |
| 문자 설정 | `/settings/notices/` | 실제 설정, 연결 상태, 현재 업무로 만든 문자 미리보기 |
| 발송 이력 | `/notices/history/` | 공급자 접수·전달·실패·불명확 상태와 시도 기록 |

인증·권한·CSRF·버전 충돌 검사를 기존 서버 기능으로 처리합니다. 실제 문자 발송은 여전히 공급자 인증정보 및 운영 설정이 필요합니다. 미리보기 조회로는 문자를 발송하지 않습니다.

## PDF 원본 확인

브라우저 내장 PDF 뷰어가 없는 환경에서도 표시하도록 로그인한 사용자에게만 로컬에서 페이지를 PNG로 렌더링합니다. 한 페이지의 긴 변은 약1400px로 제한하고 PDF는 최대100페이지, 페이지 번호를 검사합니다. 같은 웹 프로세스의 PDFium 호출은 잠금으로 직렬화합니다. 결과는 `private, no-store` 및 동일 출처 정책을 적용합니다. 원본 다운로드는 별도 유지합니다.

## 앞으로 수정할 위치

- 공통 메뉴·페이지 틀: `server/templates/base.html`
- 공통 시각 스타일: `server/static/po/workspace.css` (기존 `styles.css`와 함께 로드)
- 공통 파일 입력·PDF 페이지 조작: `server/static/po/workspace.js`
- 각 업무 화면: `server/templates/orders/`, `work/`, `intake/`, `notices/`
- PO 입력·저장: `server/static/po/orders.js`, `review.js`
- 업무 체크·일정 변경: `server/static/po/calendar.js`
- 현황 계산: `server/work/queries.py`의 `dashboard_summary`
- 원본 페이지 렌더링: `server/intake/preview.py`

날짜·수량·문자 규칙을 변경하는 요청은 화면과 서버 서비스를 함께 수정하고 테스트합니다. 실제 데이터를 목업의 샘플로 바꾸거나 브라우저 저장소로 옮기지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe ops/runtime.py
.\.venv\Scripts\python.exe server/manage.py test orders work accounts intake notices common.tests --noinput -v 1
cd server/e2e
npx.cmd playwright test
```

브라우저 테스트는 별도 테스트 DB를 사용합니다. 운영 중인 고객 PO를 등록·수정하여 검증하지 않습니다.

최종 확인: 서버78개 테스트 통과, 전체 브라우저20개 시나리오 통과. PNG 미리보기 보완 후 프론트엔드 시나리오4개(1440/1280/768/360px)를 다시 실행해 통과했습니다. 캡처를 열어 PC·모바일 레이아웃과 원본 페이지 표시도 확인했습니다. 실제 로컬 서버를 재시작해 적용했습니다.

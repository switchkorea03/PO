# PO Core and Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 수동 PO 입력·수량·회차·업무 달력·완료 상태를 DB에 저장하고 내부 사용자끼리 공동 관리한다.

**Architecture:** Django 서비스 함수가 PO와 업무를 트랜잭션으로 변경한다. 날짜 계산은 순수 함수, 화면은 Django templates와 작은 JavaScript 모듈로 분리한다. 변경 이벤트는 같은 DB 트랜잭션에 기록해 이후 문자 계획자가 소비한다.

**Tech Stack:** Python 3.12, Django 5.2 LTS, PostgreSQL 17, psycopg 3, vanilla JavaScript, Playwright.

**Spec:** [설계](../specs/2026-10-16-po-management-calendar-design.md), [상위 실행계획](2026-10-16-po-management-implementation.md).

## Global Constraints

상위 계획의 Global Constraints 전체를 적용한다. “달력 업무 완료와 회차 출고 완료는 별개다.” “한국시간(Asia/Seoul)의 날짜를 사용한다.” 국내는 품목별 납기, 해외는 수령일·ETD를 사용하며 ETA를 계산 기준으로 사용하지 않는다.

## Review Focus

상위 Review Focus 1·5를 Task 2·6·7에서 검증한다. 수량 정밀도·완료 이력·수동 날짜·ETD 삭제는 Task 2–5에서 고정한다.

---

## 공통 계약: Task 1에서 정의

`common/contracts.py`는 다음 dataclass/enum을 정의한다. ID는 UUID, 날짜는 `datetime.date`, 시각은 timezone-aware `datetime`, 수량·금액은 `Decimal`이다. JSON에서 Decimal은 문자열, 날짜는 ISO `YYYY-MM-DD`로 전달한다.

- `OrderType = domestic | overseas`, `ERPType = domestic | export | unspecified`.
- `LineInput(id: UUID|None, code: str, name: str, quantity: Decimal, unit: str, unit_price: Decimal|None, currency: str, source_amount: Decimal|None, requested_due: date|None)`.
- `OrderInput(customer_id: UUID, po_number: str, order_type: OrderType, erp_type: ERPType, ordered_on: date|None, received_on: date|None, contact: str, note: str, lines: tuple[LineInput,...])`.
- `ShipmentInput(id: UUID|None, ship_on: date|None, etd: date|None, eta: date|None, allocations: dict[UUID,Decimal])`.
- `TaskKind`: `domestic_share`, `domestic_request`, `domestic_statement`, `domestic_excel`, `domestic_voucher`, `overseas_invoice`, `overseas_bl_eta`, `overseas_erp`, `overseas_mail`, `overseas_excel`.
- `TaskSpec(order_id: UUID, shipment_id: UUID|None, kind: TaskKind, basis_on: date|None, auto_on: date|None, title: str, substeps: tuple[str,...])`.
- `OrderSnapshot(id: UUID, order_type: OrderType, erp_type: ERPType, currency: str, received_on: date|None, lines: tuple[LineInput,...], shipments: tuple[ShipmentInput,...])`.
- `TaskView(id: UUID, order_id: UUID, shipment_id: UUID|None, customer_id: UUID, customer_name: str, po_number: str, kind: TaskKind, title: str, effective_on: date|None, open_steps: tuple[str,...], state: str, suspended: bool, notice_revision: int, row_version: int)`.
- `NoticeCandidate`는 `TaskView`와 같은 필드 중 문자에 필요한 id·customer_name·po_number·title·effective_on·open_steps·notice_revision만 갖는다.
- `common/errors.py`: `ValidationError`, `VersionConflict`, `AllocationExceeded`, `AlreadyShipped`를 정의하고 HTTP 응답을 각각 422·409·422·422로 변환한다.
- `common/events.py`: `record_change(order_id: UUID, affected_task_ids: tuple[UUID,...], actor_id: int, occurred_at: datetime) -> UUID`. DB `ChangeEvent`에 저장한다. rollback되면 이벤트도 없어야 한다.
- `common/clock.py`: `today_kst(now: datetime) -> date`. 테스트는 시계를 주입하며 서버 OS의 날짜를 직접 사용하지 않는다.

## Task 1: 인증·DB·모델과 실행 골격

**Files:** Create `server/manage.py`, `server/requirements.in`, `server/requirements.lock`, `server/.env.example`, `server/README.md`, `server/config/{settings.py,urls.py,wsgi.py}`, `server/common/{contracts.py,errors.py,events.py,clock.py,audit.py}`, `server/accounts/{views.py,urls.py,tests.py}`, `server/orders/models.py`, `server/work/models.py`, `server/orders/tests/{factories.py,test_models.py}`, `server/templates/{base.html,registration/login.html}` 및 migrations.

**Interfaces:** Produces 위 공통 계약, Django User, Customer, Order, OrderLine, Shipment, ShipmentLine, Task, Substep, AuditEntry, ChangeEvent. AuditEntry와 ChangeEvent 모델은 orders/models.py에 정의하고 common 모듈은 기록 함수를 제공한다. `orders.tests.factories`: `make_order(order_type='domestic', quantities=('100',), dues=('2026-10-19',), received_on='2026-10-18') -> Order`, `make_shipment(order: Order, quantity: str, ship_on: str|None=None, etd: str|None=None) -> Shipment`. fixture는 샘플 고객과 lines도 만든다.

- [ ] **Step 1:** Python 3.12 가상환경·PostgreSQL 테스트 DB를 준비하고 Django·psycopg·python-dotenv·Waitress·pip-tools를 requirements.in에 선언한다. `pip-compile --generate-hashes --output-file requirements.lock requirements.in`, `pip-sync requirements.lock`으로 재현 가능하게 설치한다. `.env.example`에는 가짜 값만 넣고 실제 .env·media·DB dump·가상환경을 gitignore에 추가한다.
- [ ] **Step 2:** `accounts.tests.AccessTests`에서 비로그인 PO·원본·업무·전화번호 접근은 차단, 일반 사용자의 계정 관리 403, 등록된 일반 사용자의 공동 PO 조회 200을 검증한다. `orders.tests.test_models.ModelTests`는 `Decimal('0.1') * Decimal('0.2') == Decimal('0.02')`, 비양수 수량 거부, 같은 업무 scope·kind 중복 거부를 검증한다.
- [ ] **Step 3:** `python manage.py test accounts orders.tests.test_models -v 2`가 미구현 동작으로 실패함을 확인한다.
- [ ] **Step 4:** 모델·인증·권한과 보호된 최소 PO 페이지를 구현한다. 수량·금액은 DecimalField(30,10)를 구현 기본값으로 두고 입력 소수 10자리 초과는 반올림 없이 명시적 오류로 돌린다. 실제 샘플이 이 정밀도를 넘으면 필드와 관련 테스트의 정밀도를 확대하고 값 손실 없이 등록한다. 부족한 고객·번호·품목·수량·단위·국내 납기·해외 수령일은 등록 오류다. 단가 미인식은 공란과 확인 표시로 보존한다. Order/Shipment/Task에는 row_version을 둔다. Task.scope_key는 `order:<id>` 또는 `shipment:<id>`의 non-null 문자열로 만들고 `(scope_key,kind)`를 고유제약으로 잡는다. 원본·전화번호는 인증된 경로로만 제공한다.
- [ ] **Step 5:** `python manage.py makemigrations`, `python manage.py migrate`, Step 3 테스트를 실행해 통과를 확인한다. admin과 사내 사용자 계정을 분리한다. 최소 목록 페이지가 DB 조회 후 렌더되는지 확인한다.
- [ ] **Step 6:** Files와 생성 migrations·gitignore 변경만 `feat: add authenticated PO persistence foundation`으로 커밋한다.

## Task 2: PO·회차·수량·수정본의 트랜잭션

**Files:** Create `server/orders/{services.py,queries.py}`, `server/orders/tests/{test_services.py,test_conflicts.py}`; Modify `server/common/audit.py`.

**Interfaces:** Consumes Task 1. Produces `save_order(data: OrderInput, actor_id: int, expected_version: int|None, order_id: UUID|None=None) -> Order`, `save_shipment(order_id: UUID, data: ShipmentInput, actor_id: int, expected_version: int|None) -> Shipment`, `confirm_shipment(shipment_id: UUID, actor_id: int, expected_version: int) -> Shipment`, `cancel_remaining(line_id: UUID, quantity: Decimal, actor_id: int, expected_version: int) -> OrderLine`, `correct_shipment(shipment_id: UUID, allocations: dict[UUID,Decimal], reason: str, actor_id: int, expected_version: int) -> Shipment`, `cancel_order(order_id: UUID, actor_id: int, expected_version: int) -> Order`.

- [ ] **Step 1:** `QuantityTests.test_single_quantity_and_confirmation`에 주문 100·회차 70/30 등록 후 완료 전 출고 0/잔량100, 1차 완료 후 출고70/잔량30을 assert한다. `test_overallocation_and_reduction`은 회차70/40 거부, 70개 완료 후 주문60 수정 거부를 assert한다. `test_cancel_and_correction`은 미출고30 취소 후 출고70/취소30/남은 출고대상0과 정정 사유·이력을 assert한다.
- [ ] **Step 2:** `ConflictTests`는 TransactionTestCase와 두 DB 연결로 동시에 70·40 배정할 때 하나만 성공하고 합계가100 이하임을 검증한다. row_version이 오래된 저장은409, 잘못된 다른 PO 품목을 회차에 넣으면422, 출고 완료 재요청은 실적 중복 없이 같은 결과임을 검증한다. `python manage.py test orders.tests.test_services orders.tests.test_conflicts -v 2`로 실패를 확인한다.
- [ ] **Step 3:** 위 서비스 함수를 구현한다. 부모 PO·관련 품목을 일관된 순서로 select_for_update하고 version을 비교한다. 취소 후 배정 합계는 `주문수량-취소수량` 이하여야 한다. 이미 배정된 잔량 취소는 대상 미완료 회차를 먼저 줄이도록 오류를 반환한다. 출고실적 직접 덮어쓰기 대신 사유 필수 정정 이력을 만든다. 완료 회차 삭제는 막는다. 수정본은 동일 품목 ID를 유지하여 비교 반영하며 실적이 있는 품목 삭제를 막는다. 모든 변경과 ChangeEvent를 같은 트랜잭션에 기록한다.
- [ ] **Step 4:** 고객·PO·국내 납기별 초기 회차 생성, 고객 기본값 재정의, 통화와 국내외 독립, 원문금액 불일치·단위 무환산을 테스트하고 Step 2 테스트 전체를 통과시킨다. Task 4 전까지 ChangeEvent는 보관만 한다.
- [ ] **Step 5:** `feat: add PO shipment quantities and audited revisions`로 커밋한다.

## Task 3: 날짜 엔진과 고정 업무 목록

**Files:** Create `server/work/{rules.py,catalog.py}`, `server/work/tests/test_rules.py`.

**Interfaces:** Consumes OrderSnapshot/TaskSpec. Produces `next_week_tuesday(value: date) -> date`, `next_weekday(value: date) -> date`, `previous_weekday(value: date) -> date`, `build_task_specs(order: OrderSnapshot) -> tuple[TaskSpec,...]`. catalog는 TaskKind별 설계 §5·6의 문구·세부 작업·ERP 안내를 반환한다.

- [ ] **Step 1:** 다음 assert를 `DateRulesTests`의 파라미터 사례로 작성한다.

```python
assert previous_weekday(date(2026,10,19)) == date(2026,10,16)
assert next_week_tuesday(date(2026,10,18)) == date(2026,10,20)
assert next_week_tuesday(date(2026,10,19)) == date(2026,10,27)
for day in (16,17,18):
    assert next_weekday(date(2026,10,day)+timedelta(days=1)) == date(2026,10,19)
```

- [ ] **Step 2:** `SpecTests`는 국내 회차당 준비2/당일3, 해외 PO당 접수1/BL1·회차당 후속3, ETD 없으면 후속 auto_on=None, ETA 변경은 결과 불변, 해외 요청납기 표시 없음, 국내 USD 수출 메뉴·기타통화 미지정 메뉴 없음, 월경계·연경계·윤일·무효 날짜 거부를 assert한다. `python manage.py test work.tests.test_rules -v 2`로 실패 확인한다.
- [ ] **Step 3:** 순수 date 연산으로 구현한다. 수령일은 보정 전에 차주 화요일을 계산한다. 국내 준비일은 출고일의 직전 평일, ETD 후속은 ETD+1을 다음 평일로 보정한다. 국내 납기 표시는 별도 read model이며 완료 가능한 Task를 만들지 않는다. 고정 문구를 임의 편집하는 목업의 규칙 설정 기능은 가져오지 않는다.
- [ ] **Step 4:** Step 2 명령에서 모든 사례 통과를 확인한다. 같은 Snapshot에 항상 같은 scope·kind·날짜가 나오는지 검증한다.
- [ ] **Step 5:** `feat: implement approved PO calendar date rules`로 커밋한다.

## Task 4: 재계산·수동 이동·ETD 미정 전환

**Files:** Create `server/work/services.py`, `server/work/tests/test_reconcile.py`; Modify `server/orders/services.py`.

**Interfaces:** Produces `reconcile_order(order_id: UUID, actor_id: int) -> tuple[TaskView,...]`, `move_task(task_id: UUID, target_on: date|None, actor_id: int, expected_version: int) -> TaskView`(None=자동 일정 복귀), `review_completed_task(task_id: UUID, reopen: bool, actor_id: int, expected_version: int) -> TaskView`.

- [ ] **Step 1:** `ReconcileTests`는 반복 저장의 Task ID·개수 동일, 기준일 변경 시 미완료만 이동, 완료일 보존·needs_review=True, 수동일 유지·재계산 표시, 자동 복귀, 과거 등록 지연을 assert한다. ETD 삭제 시 미완료 suspended=True/effective_on=None, 수동일은 기록으로 보존하되 알림용 effective_on=None, 완료 Task는 기존 기록 유지임을 assert한다.
- [ ] **Step 2:** `python manage.py test work.tests.test_reconcile -v 2`로 실패를 확인한다.
- [ ] **Step 3:** Task 3의 specs를 scope·kind로 upsert한다. Task 2의 변경 트랜잭션 안에서 호출하고 affected task IDs를 ChangeEvent에 기록한다. 완료 후 기준일·수량 등 의존 값 변경은 재확인만 표시한다. 미완료 상태와 최종 업무일의 의미가 달라질 때 notice_revision을 증가시키되 단순 재저장은 증가시키지 않는다. ETD 재입력 시 수동일은 숨겨진 채 자동 복구하지 않고 사용자가 자동 계산일 채택 또는 이전 수동일 재확정을 선택하도록 표시한다. 회차 취소·PO취소 시 미완료는 취소하고 완료는 유지한다.
- [ ] **Step 4:** Task 2–4 테스트를 함께 통과시킨다. Task·이력·ChangeEvent 중 하나라도 실패하면 전체 rollback되는 사례를 포함한다.
- [ ] **Step 5:** `feat: preserve manual and completed work during rescheduling`로 커밋한다.

## Task 5: 세부 체크와 재작업 상태

**Files:** Create `server/work/tests/test_completion.py`; Modify `server/work/services.py`.

**Interfaces:** Produces `set_substep(substep_id: UUID, done: bool, actor_id: int, expected_version: int) -> TaskView`. Task 4의 review_completed_task를 사용한다.

- [ ] **Step 1:** `CompletionTests`에서 인보이스 작업만 완료하면 partial, ERP까지 완료하면 done, 완료자·시각 보존, 체크만으로 출고실적 불변을 assert한다. 재확인만 있는 done 업무는 알림 후보 제외, reopen 시 미완료로 복귀하고 과거 이력이 남음을 검증한다.
- [ ] **Step 2:** `python manage.py test work.tests.test_completion -v 2`로 실패를 확인한다.
- [ ] **Step 3:** 세부 체크·상위 상태·이력·ChangeEvent를 같은 트랜잭션에 반영한다. 취소된 업무 체크는 거부한다. 전체 완료 여부는 세부 작업에서 파생하며 부분완료는 알림상 미완료다. 재작업 시 이전 체크 이력은 보존하고 새 수행 상태를 초기화한다.
- [ ] **Step 4:** Step 2 테스트 및 work 전체 테스트에서 실패0을 확인한다.
- [ ] **Step 5:** `feat: add partial completion and explicit rework`로 커밋한다.

## Task 6: 보호된 조회·변경 API와 달력 묶음

**Files:** Create `server/orders/{forms.py,views.py,urls.py}`, `server/work/{queries.py,views.py,urls.py}`, `server/work/tests/test_calendar.py`; Modify `server/orders/queries.py`, `server/config/urls.py`.

**Interfaces:** Produces `list_tasks(start: date, end: date, customer_id: UUID|None, order_type: OrderType|None) -> tuple[TaskView,...]`, `get_notice_candidates(on: date, include_overdue: bool) -> tuple[NoticeCandidate,...]`(날짜미정·suspended·done·cancelled 제외). GET `/orders/`, `/orders/<id>/`, `/calendar/`, `/api/calendar/?start=&end=&customer=&type=`. POST `/orders/new/`, `/orders/<id>/edit/`, `/orders/<id>/shipments/`, `/shipments/<id>/confirm/`, `/orders/<id>/cancel/`, `/lines/<id>/cancel-remaining/`, `/shipments/<id>/correct/`, `/tasks/<id>/move/`, `/tasks/<id>/review/`, `/substeps/<id>/check/`. 변경 요청은 CSRF·row_version 필수.

- [ ] **Step 1:** `CalendarTests`에서 같은 날짜 A·B·A의 domestic_share 표시가 `A,B(출고 내역 공유)`, 하위업무3개 유지·일부완료 partial을 assert한다. 동명 고객은 customer_id·PO로 상세 구별, 국내 품목 납기만 표시, 필터·월간·주간 범위·지연·날짜미정·원문 날짜 노출을 검증한다.
- [ ] **Step 2:** 모든 POST의 비로그인 차단·CSRF 거부·동시수정409·유효성422를 검증하고 `python manage.py test work.tests.test_calendar accounts -v 2`로 실패를 확인한다.
- [ ] **Step 3:** 변경 endpoint는 Task 2·4·5 서비스만 호출한다. 묶음은 표시용이며 underlying task IDs를 반환하고 고객명 중복은 표시에서만 제거한다. 고객·PO·품목·잔량·진행상태 검색을 구현한다. KST today를 공통 clock에서 가져온다.
- [ ] **Step 4:** 위 테스트를 통과시키고 `get_notice_candidates(date(2026,10,19),True)`에 오늘·이전 미완료만 포함되고 납기 표시가 섞이지 않는지 assert한다.
- [ ] **Step 5:** `feat: expose filtered PO calendar and protected work actions`로 커밋한다.

## Task 7: 실사용 PO 화면과 달력

**Files:** Create `server/templates/orders/{list.html,form.html,detail.html}`, `server/templates/work/{calendar.html,detail.html}`, `server/static/po/{styles.css,api.js,orders.js,calendar.js}`, `server/e2e/{package.json,package-lock.json,playwright.config.mjs,core.spec.mjs}`; Modify `server/templates/base.html`, `server/README.md`.

**Interfaces:** Consumes Task 6의 endpoint·TaskView. `api.js`: `postJson(url, payload) -> Promise<object>`; CSRF와409/422 안내를 공통 처리한다. e2e는 테스트 DB와 fake 시간·계정을 사용하고 운영 DB를 사용하지 않는다.

- [ ] **Step 1:** Playwright `core.spec.mjs`에 로그인→서로 다른 고객·같은 납기의 PO 등록→회차70/30→70출고 완료→잔량30 확인→월요일 출고 준비 금요일 확인→세부 일부완료→수동 이동→새로고침 후 보존 흐름을 작성한다. `npx playwright test core.spec.mjs`의 UI 부재 실패를 확인한다.
- [ ] **Step 2:** 기존 `po-calendar/dist/styles.css`를 새 styles.css로 복사해 화면 스타일을 조정한다. 샘플 상태·고정 TODAY·ETA 기준·데모 초기화는 가져오지 않는다. Django forms로 다품목 편집·회차 추가·잔량 취소·실적 정정·원문금액 비교·ERP 안내를 제공한다. 일정 이동은 날짜 입력을 필수 제공하고 드래그는 선택 보조로만 둔다.
- [ ] **Step 3:** 월간·주간·날짜별 목록, 고객·국내외 필터, 긴 문구 상세, 부분완료·지연·재확인·날짜미정·수동 지정·충돌 안내를 구현한다. 예외는 텍스트로 표시하며 키보드로 조회·체크·날짜 수정을 할 수 있게 한다.
- [ ] **Step 4:** `npx playwright test core.spec.mjs`를1440/1280/768/360px에서 통과시킨다. 각 폭에서 `document.documentElement.scrollWidth <= window.innerWidth`를 확인하고, 작은 화면은 업무 목록을 우선 노출한다. 새로고침 후 PO·완료 상태 유지와 보호된 접근을 확인한다.
- [ ] **Step 5:** `python manage.py test -v 2`와 E2E를 통과시키고 `feat: ship persistent PO management and work calendar`로 커밋한다. 수동 입력으로만 작동하는 1차 결과를 시연한다. 파일 인식·문자 미연결 상태는 README에 명시한다.


# PO Automation Dynamic UI Mockup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 승인된 B1·D1·P1 구조로 국내·해외 PO 업무의 정상·예외 상태를 클릭해 탐색할 수 있는 상세 동적 UI 목업을 만든다.

**Architecture:** 빌드가 필요 없는 정적 SPA로 구현하고 hash router, 중앙 샘플 상태 저장소와 화면별 렌더 함수를 분리한다. 실제 ERP·Outlook·OCR·파일시스템 대신 명시적인 mock action을 사용하며 모든 상태는 브라우저 메모리에만 존재하고 초기화할 수 있다. UI 상태 규칙은 순수 함수로 분리해 Node 내장 테스트로 검증한다.

**Tech Stack:** Semantic HTML, CSS custom properties, ES modules, browser History/Hash APIs, Node.js built-in test runner, private static Site hosting

**Spec:** `docs/superpowers/specs/2026-10-13-po-automation-ui-mockup-design.md`

## Global Constraints

- 레이아웃은 B1 대시보드, D1 주문 상세, P1 PO 검토를 사용한다.
- PC 1440px 우선, 1280px 유지, 태블릿 상하 전환, 모바일 조회·간단 승인 중심으로 반응형 처리한다.
- 실제 ERP, Outlook, OCR, 파일 업로드, 문서 생성, 인증, DB 연결을 구현하지 않는다.
- 수신메일 검색·판독, BL 업로드·저장·OCR, 공유 Excel 읽기·쓰기·완료추적 UI를 만들지 않는다.
- QY 번호는 `QY{EXW:yyMMdd}-{sequence}{customerCode}({VSL|AIR})`를 유지한다.
- 해외 순서는 `QY 생성·발송 → 중국 공장 회신 확인 → QP·선적정보 수동입력 → QY 연결확정 → 고객메일 → 수입선적등록 → 입고처리 → 내부메일`이다.
- 생산요청 수량은 사용자가 직접 입력하고 담당자가 단독 승인한다. 부족량·FCST·안전재고를 자동계산하지 않는다.
- 완료값은 직접 수정하지 않고 정정업무를 만든다.
- 색상만으로 상태를 전달하지 않고 아이콘·텍스트·ARIA 상태를 함께 제공한다.
- 목업의 모든 데이터는 비식별 샘플이며 새로고침 또는 초기화 버튼으로 복원할 수 있다.

## Review Focus

- 국내/해외 주문 전환 시 D1 공통 골격은 유지되고 업무별 본문과 단계만 바뀌어야 한다. Task 3과 4의 route rendering 테스트로 고정한다.
- 부분출고 실제수량 합계가 PO 수량을 넘으면 저장이 차단되고 잔량이 음수가 되지 않아야 한다. Task 3의 상태 테스트로 고정한다.
- QY 발송 전에는 공장 회신이나 QP 입력으로 건너뛸 수 없고, QP 불일치가 있으면 후속 단계가 잠겨야 한다. Task 4의 workflow 테스트로 고정한다.
- 완료 건 수정은 원본을 바꾸지 않고 정정업무를 추가해야 한다. Task 5의 correction 테스트로 고정한다.
- 360px 모바일에서 핵심 조회·승인 화면에 가로 스크롤이나 가려진 주요 버튼이 없어야 한다. Task 6의 브라우저 검증으로 고정한다.

---

## File Structure

```text
ui-mockup/
  package.json
  dist/
    index.html                    # SPA 진입점과 공통 app root
    assets/
      styles.css                 # 토큰, 레이아웃, 컴포넌트, 반응형
      app.js                     # 초기화, 이벤트 위임, 렌더 루프
      router.js                  # hash route 파싱과 이동
      store.js                   # 샘플 상태, dispatch, reset
      formatters.js              # 수량·금액·날짜 포맷
      components.js              # shell, badge, table, stepper, modal
      screens/
        dashboard.js             # B1 오늘의 업무
        orders.js                # PO 목록
        po-review.js             # P1 원본/필드 연동
        order-detail.js          # D1 공통 상세 골격
        domestic.js              # 재고·생산요청·분할납품
        overseas.js              # QY·회신대기·QP·후속업무
        operations.js            # 문서·메일·예외·정정·Excel 복사
        master-data.js           # 기준정보
  tests/
    router.test.mjs
    store.test.mjs
    domestic.test.mjs
    overseas.test.mjs
    completion.test.mjs
  README.md
.openai/hosting.json             # private static Site configuration
```

### Task 1: Static SPA Shell, Design Tokens, Router, and Sample Store

**Files:**
- Create: `ui-mockup/package.json`
- Create: `ui-mockup/dist/index.html`
- Create: `ui-mockup/dist/assets/{styles,app,router,store,formatters,components}.js`
- Create: `ui-mockup/tests/{router,store}.test.mjs`
- Test: `ui-mockup/tests/router.test.mjs`, `ui-mockup/tests/store.test.mjs`

**Interfaces:**
- Consumes: UI design sections 2, 3, 11, 12
- Produces: `parseRoute(hash) -> Route`, `navigate(path)`, `getState()`, `dispatch(action)`, `subscribe(listener)`, `resetDemo()`, `renderShell(content, context)`

- [ ] **Step 1: Write failing router and reset tests**

```js
test('parses domestic order detail route', () =>
  assert.deepEqual(parseRoute('#/orders/BJ-10241'), {screen:'order-detail', id:'BJ-10241'}));

test('resetDemo restores initial orders without sharing mutable references', () => {
  dispatch({type:'DELIVERY_CONFIRMED', orderId:'BJ-10241', quantity:2000});
  resetDemo();
  assert.equal(getState().orders['BJ-10241'].deliveredQuantity, 6000);
});
```

- [ ] **Step 2: Run tests and verify failure**

Run: `node --test ui-mockup/tests/router.test.mjs ui-mockup/tests/store.test.mjs`
Expected: FAIL because router and store modules do not exist.

- [ ] **Step 3: Implement shell, router, store, and tokens**

Add the approved left navigation, top safe-mode indicators, reusable state badges, modal, toast, stepper, table and responsive breakpoints. Seed 범진전자 and CHEMTRO VINA normal, warning and exception scenarios.

- [ ] **Step 4: Run tests**

Run: `node --test ui-mockup/tests/router.test.mjs ui-mockup/tests/store.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ui-mockup/package.json ui-mockup/dist ui-mockup/tests/router.test.mjs ui-mockup/tests/store.test.mjs
git commit -m "feat: scaffold dynamic PO UI mockup"
```

### Task 2: B1 Dashboard and PO List

**Files:**
- Create: `ui-mockup/dist/assets/screens/dashboard.js`
- Create: `ui-mockup/dist/assets/screens/orders.js`
- Modify: `ui-mockup/dist/assets/app.js`
- Modify: `ui-mockup/dist/assets/styles.css`
- Test: `ui-mockup/tests/store.test.mjs`

**Interfaces:**
- Consumes: `getState()`, `navigate(path)`, `renderShell()`
- Produces: `renderDashboard(state)`, `renderOrders(state, filters)`, actions `FILTER_CHANGED|ORDER_OPENED`

- [ ] **Step 1: Write failing priority and filter tests**

```js
test('dashboard prioritizes blocked and due-today work before later work', () => {
  assert.deepEqual(selectPriorityWork(seedState).map(x => x.id).slice(0,2), ['EX-003','BJ-10241']);
});

test('order filter combines owner status and domestic-overseas type', () => {
  assert.deepEqual(filterOrders(seedState.orders,{owner:'김영업',type:'overseas',status:'shipment-ready'}).map(x=>x.id), ['CV-8821']);
});
```

- [ ] **Step 2: Run test and verify failure**

Run: `node --test ui-mockup/tests/store.test.mjs`
Expected: FAIL because dashboard selectors are absent.

- [ ] **Step 3: Implement B1 dashboard and searchable order list**

Render summary counts, priority work, today/tomorrow schedule, domestic/overseas filters, search, status chips and row navigation. Use real Korean labels and approved sample states.

- [ ] **Step 4: Run tests**

Run: `node --test ui-mockup/tests/store.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ui-mockup/dist/assets/screens/dashboard.js ui-mockup/dist/assets/screens/orders.js ui-mockup/dist/assets/app.js ui-mockup/dist/assets/styles.css ui-mockup/tests/store.test.mjs
git commit -m "feat: add dashboard and PO worklist mockups"
```

### Task 3: P1 PO Review, Revision Compare, and Domestic D1 Workflow

**Files:**
- Create: `ui-mockup/dist/assets/screens/{po-review,order-detail,domestic}.js`
- Modify: `ui-mockup/dist/assets/{app,store,styles}.js`
- Create: `ui-mockup/tests/domestic.test.mjs`

**Interfaces:**
- Consumes: shell/components/store; route order ID
- Produces: `renderPoReview(state)`, `renderOrderDetail(order)`, `renderDomestic(order)`, actions `FIELD_SELECTED|FIELD_CONFIRMED|REVISION_APPROVED|DELIVERY_ROUND_ADDED|DELIVERY_CONFIRMED|PRODUCTION_APPROVED`

- [ ] **Step 1: Write failing domestic-state tests**

```js
test('field selection links extracted value to matching source region', () =>
  assert.equal(selectSourceRegion(poReview,'quantity').id,'pdf-region-quantity'));

test('delivery confirmation blocks total above ordered quantity', () =>
  assert.throws(() => confirmDelivery(domesticOrder, 7000), /PO 수량을 초과/));

test('approved production request uses only the user-entered quantity', () =>
  assert.equal(approveProduction({enteredQuantity:5000, stock:3500}).quantity,5000));
```

- [ ] **Step 2: Run test and verify failure**

Run: `node --test ui-mockup/tests/domestic.test.mjs`
Expected: FAIL because review and domestic state functions are absent.

- [ ] **Step 3: Implement P1 review and revision screens**

Create linked PDF placeholder regions, extracted fields, confidence states, keyboard navigation, duplicate-blocked modal and existing/new revision diff. Lock already delivered values.

- [ ] **Step 4: Implement D1 domestic detail and interactions**

Use the domestic stepper, action rail, stock reference, explicit production quantity, +14-day default, single approval, split-delivery rows, actual quantity confirmation, purchase-mail state and correction entry.

- [ ] **Step 5: Run tests**

Run: `node --test ui-mockup/tests/domestic.test.mjs`
Expected: PASS including over-delivery prevention.

- [ ] **Step 6: Commit**

```bash
git add ui-mockup/dist/assets/screens ui-mockup/dist/assets/app.js ui-mockup/dist/assets/store.js ui-mockup/dist/assets/styles.css ui-mockup/tests/domestic.test.mjs
git commit -m "feat: add PO review and domestic workflow mockups"
```

### Task 4: Overseas D1 QY–Factory Reply–QP Workflow

**Files:**
- Create: `ui-mockup/dist/assets/screens/overseas.js`
- Modify: `ui-mockup/dist/assets/{app,store,styles}.js`
- Create: `ui-mockup/tests/overseas.test.mjs`

**Interfaces:**
- Consumes: D1 order-detail shell, `dispatch`, CHEMTRO sample order
- Produces: `renderOverseas(order)`, `formatQyNumber(input)`, `suggestQyLinks(qp, qyInvoices)`, `canAdvanceOverseas(order)`, actions `QY_ISSUED|QY_DRAFT_CREATED|FACTORY_REPLY_CONFIRMED|QP_RECORDED|QY_LINK_CONFIRMED|SHIPMENT_DISCREPANCY_CONFIRMED|OVERSEAS_STEP_COMPLETED`

- [ ] **Step 1: Write failing number and sequence tests**

```js
test('formats the validated QY number without changing the original rule', () =>
  assert.equal(formatQyNumber({exw:'2026-10-13',sequence:40,customerCode:'CHVN',mode:'VSL'}),'QY261013-40CHVN(VSL)'));

test('cannot enter QP before QY was sent and factory reply was confirmed', () =>
  assert.equal(canAdvanceOverseas({stage:'qy-draft'}).next,'send-qy'));

test('date or quantity discrepancy locks customer mail and ERP follow-up', () =>
  assert.equal(canAdvanceOverseas(discrepantShipment).blocked,true));
```

- [ ] **Step 2: Run test and verify failure**

Run: `node --test ui-mockup/tests/overseas.test.mjs`
Expected: FAIL because overseas workflow functions are absent.

- [ ] **Step 3: Implement QY issue, draft, and factory-wait states**

Show EXW date, VSL/AIR, customer code, sequence, QY preview, document and recipient checks. After mock sending, change the action rail to `중국 공장 회신 확인`; do not simulate inbox polling.

- [ ] **Step 4: Implement QP input, link suggestions, and discrepancies**

Accept user-entered QP, ON BOARD, ETD, ETA status and actual quantity. Support 1:1 suggestion and explicit many-to-many selection; ignore the Chinese suffix as a key. Lock follow-up until discrepancies receive a reason and confirmation.

- [ ] **Step 5: Implement ordered follow-up interactions**

Allow customer notice → import shipment → receipt → internal mail in order, each as an explicitly labeled mock action with completed audit event.

- [ ] **Step 6: Run tests**

Run: `node --test ui-mockup/tests/overseas.test.mjs`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add ui-mockup/dist/assets/screens/overseas.js ui-mockup/dist/assets/app.js ui-mockup/dist/assets/store.js ui-mockup/dist/assets/styles.css ui-mockup/tests/overseas.test.mjs
git commit -m "feat: add overseas QY and QP workflow mockups"
```

### Task 5: Documents, Outbound Mail, Exceptions, Corrections, Excel Copy, and Master Data

**Files:**
- Create: `ui-mockup/dist/assets/screens/{operations,master-data}.js`
- Modify: `ui-mockup/dist/assets/{app,store,styles}.js`
- Create: `ui-mockup/tests/completion.test.mjs`

**Interfaces:**
- Consumes: orders, documents, mail operations, current role
- Produces: `renderOperations(route,state)`, `renderMasterData(state)`, `canCompleteOrder(order)`, `createCorrection(order,change,reason)`, actions `MAIL_DRAFT_CREATED|MANUAL_ERP_RECORDED|EXCEPTION_RESOLVED|CORRECTION_CREATED|COPY_ROW`

- [ ] **Step 1: Write failing completion and correction tests**

```js
test('Excel copy status is not required for order completion', () =>
  assert.equal(canCompleteOrder({...completeOrder, excelCopied:false}),true));

test('completed record remains immutable and correction keeps before-after-reason', () => {
  const result=createCorrection(completeOrder,{actualQuantity:3900},'현장 수량 정정');
  assert.equal(result.original.actualQuantity,4000);
  assert.equal(result.correction.after.actualQuantity,3900);
});
```

- [ ] **Step 2: Run test and verify failure**

Run: `node --test ui-mockup/tests/completion.test.mjs`
Expected: FAIL because completion/correction functions are absent.

- [ ] **Step 3: Implement operations screens**

Add document versions, draft-only Outlook review, registered recipient/customer-attachment checks, manual ERP record, owner-only exceptions, immutable corrections and audit timeline.

- [ ] **Step 4: Implement Excel copy and master-data screens**

Excel copy view exposes only salesperson/customer/model/currency/price/actual date/final quantity with row/all copy controls. Master-data screens cover customers, items, units, templates and outbound recipients without secrets.

- [ ] **Step 5: Run tests**

Run: `node --test ui-mockup/tests/completion.test.mjs`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ui-mockup/dist/assets/screens ui-mockup/dist/assets/app.js ui-mockup/dist/assets/store.js ui-mockup/dist/assets/styles.css ui-mockup/tests/completion.test.mjs
git commit -m "feat: complete operational UI mockup screens"
```

### Task 6: Responsive, Accessibility, Browser QA, Documentation, and Private Publish

**Files:**
- Modify: `ui-mockup/dist/index.html`, `ui-mockup/dist/assets/styles.css`
- Create: `ui-mockup/README.md`
- Create: `.openai/hosting.json`
- Test: all `ui-mockup/tests/*.test.mjs` and browser routes

**Interfaces:**
- Consumes: all mockup screens and state transitions
- Produces: documented local entry point, responsive/accessibility-complete static bundle, private deployed URL when Sites publication is available

- [ ] **Step 1: Run the full automated test suite**

Run: `node --test ui-mockup/tests/*.test.mjs`
Expected: PASS with zero failed tests.

- [ ] **Step 2: Validate semantic and accessibility behavior**

Check landmark structure, one H1 per route, label/input associations, keyboard focus order, visible focus, modal focus return, status live regions and non-color status labels.

- [ ] **Step 3: Validate responsive routes in a browser**

Check dashboard, P1 review, domestic D1, overseas D1, exception and Excel-copy routes at 1440×900, 1280×800, 768×1024 and 360×800. Expected: no clipped primary action; mobile converts P1 to stacked mode.

- [ ] **Step 4: Write developer handoff**

Document route inventory, component mapping, sample-state actions, how to reset, known mock-only behavior and direct links to the UI design and validated business design.

- [ ] **Step 5: Package and publish privately**

Use `ui-mockup/dist` as the static directory, preserve private audience, and verify the returned deployment URL. If publication tooling is unavailable, provide the verified local artifact and state that limitation.

- [ ] **Step 6: Commit**

```bash
git add ui-mockup .openai/hosting.json
git commit -m "docs: finalize and publish PO UI mockup"
```

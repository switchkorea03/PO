import { parseRoute } from './router.js';
import { getState, resetDemo, subscribe } from './store.js';
import { dispatch } from './store.js';
import { renderShell, showToast } from './components.js';
import { renderDashboard } from './screens/dashboard.js';
import { renderOrders } from './screens/orders.js';
import { renderPoReview } from './screens/po-review.js';
import { renderOrderDetail } from './screens/order-detail.js';
import { confirmDelivery, approveProduction } from './screens/domestic.js';
import { renderOverseas, formatQyNumber } from './screens/overseas.js';
import { renderOperations, selectExcelRows } from './screens/operations.js';
import { renderMasterData } from './screens/master-data.js';
import { escapeHtml } from './formatters.js';

const app = document.querySelector('#app');

function render() {
  const route = parseRoute();
  const focusedFilter = document.activeElement?.dataset.filter;
  const cursor = document.activeElement?.selectionStart;
  const state = getState();
  const screens = {
    dashboard: () => renderDashboard(state),
    orders: () => renderOrders(state, { ...state.filters, ...(route.query || {}) }),
    'po-review': () => renderPoReview(state),
    'order-detail': () => renderOrderDetail(state.orders[route.id], renderOverseas),
    operations: () => renderOperations(route, state),
    'master-data': () => renderMasterData(state),
    'not-found': () => `<section class="empty-state"><h1>페이지를 찾을 수 없습니다.</h1><a class="button button--primary" href="#/">오늘의 업무로 이동</a></section>`
  };
  const content = (screens[route.screen] || (() => `<section class="page-header"><div><h1>업무 화면 준비 중</h1></div></section>`))();
  const activeMap = { dashboard: '/', orders: '/orders', 'po-review': '/orders', 'order-detail': '/orders', 'master-data': '/master' };
  const active = route.screen === 'operations' ? `/operations/${route.section}` : (activeMap[route.screen] || '/orders');
  const title = route.screen === 'dashboard' ? '오늘의 업무' : route.screen === 'operations' ? '운영' : route.screen === 'master-data' ? '기준정보' : 'PO 업무';
  app.innerHTML = renderShell(content, { title, active });
  if (focusedFilter) {
    const input = app.querySelector(`[data-filter="${focusedFilter}"]`);
    input?.focus();
    if (input?.type === 'search' && cursor !== null) input.setSelectionRange(cursor,cursor);
  }
  document.body.dataset.route = route.screen;
  void state;
}

window.addEventListener('hashchange', () => { render(); window.scrollTo(0,0); });
document.addEventListener('click', event => {
  if (event.target.closest('.skip-link')) {event.preventDefault();document.querySelector('main')?.focus();return;}
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (action === 'reset-demo') { resetDemo(); showToast('데모 데이터가 초기 상태로 복원되었습니다.'); }
  if (action === 'toggle-nav') document.querySelector('.sidebar')?.classList.toggle('is-open');
  if (action === 'clear-filters') dispatch({ type: 'FILTER_CHANGED', filters: { search: '', owner: '전체', type: 'all', status: 'all' } });
  if (action === 'select-field') dispatch({ type: 'FIELD_SELECTED', field: event.target.closest('[data-field]').dataset.field });
  if (action === 'confirm-review') attempt(() => { dispatch({type:'REVIEW_CONFIRMED',orderId:'SE-2408'}); location.hash = '#/orders/SE-2408'; return 'PO 검토가 완료되었습니다.'; });
  if (action === 'edit-field') {
    const field = getState().poReview.fields.find(field=>field.key === getState().selectedField);
    openModal(`${field.label} 확인`, `<label class="field"><span>원본 확인값</span><input name="value" value="${escapeHtml(field.value)}" required></label><p class="muted">왼쪽 원본과 비교한 값을 확인합니다.</p>`, values => {dispatch({type:'FIELD_CONFIRMED',field:field.key,value:values.value});return '필드를 확인했습니다.';});
  }
  if (action === 'approve-production') {
    try { const result = approveProduction({ enteredQuantity: document.querySelector('#production-qty')?.value }); dispatch({ type: 'PRODUCTION_APPROVED', orderId: parseRoute().id, quantity: result.quantity, date:document.querySelector('#production-date')?.value }); showToast('생산요청이 승인되었습니다.'); } catch (error) { showToast(error.message); }
  }
  if (action === 'confirm-delivery') {
    const order = getState().orders[parseRoute().id];
    try { const quantity = Number(document.querySelector('#delivery-qty')?.value ?? order.quantity - order.deliveredQuantity); confirmDelivery(order, quantity); dispatch({ type: 'DELIVERY_CONFIRMED', orderId: order.id, quantity, date:document.querySelector('#actual-delivery-date')?.value }); showToast('실제 납품수량을 확정했습니다.'); } catch (error) { showToast(error.message); }
  }
  if (action === 'mock-document') openModal('문서 미리보기', '<div class="document-demo"><p class="eyebrow">DOCUMENT PREVIEW</p><h2>주문·선적 확인서</h2><p>고객사: CHEMTRO VINA / 범진전자</p><p>모델 및 수량: 업무 상세에서 확인</p><hr><p>생성 문서의 레이아웃과 버전 확인을 위한 샘플입니다.</p></div>',null);
  if (action === 'open-correction') {
    const order = getState().orders[parseRoute().id] || getState().orders['CV-8821'];
    if (order.status !== 'complete') showToast('완료된 주문에서 정정업무를 생성하세요.');
    else openModal(`${order.id} 정정업무`, `<p class="muted">원본 수량은 보존됩니다.</p><label class="field"><span>정정 후 수량</span><input name="quantity" type="number" min="1" required value="${order.actualQuantity || order.deliveredQuantity}"></label><label class="field"><span>정정 사유</span><textarea name="reason" required></textarea></label>`, values=>{dispatch({type:'CORRECTION_CREATED',orderId:order.id,...values});return '정정업무를 생성했습니다. 원본은 보존됩니다.';});
  }
  if (action === 'advance-overseas') {
    const button = event.target.closest('[data-next]');
    const step = button.dataset.next;
    const label = button.textContent.trim();
    const orderId = parseRoute().id;
    if (step === 'record-qp') saveQp(orderId);
    else if (step === 'send-qy') attempt(()=>{const values=Object.fromEntries(new FormData(document.querySelector('#qy-form'))); dispatch({type:'QY_DRAFT_CHANGED',orderId,...values});dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId,step,label});return 'QY 발송을 기록했습니다.';});
    else if (step === 'import-register' || step === 'receipt') openModal(label,step === 'import-register' ? '<label class="field"><span>iCUBE 등록번호</span><input name="erpNumber" required placeholder="IMP-2026-001"></label><label class="field"><span>수동 처리 사유</span><textarea name="reason" required></textarea></label>' : '<label class="field"><span>실제 입고일</span><input name="date" type="date" required value="2026-10-22"></label>',values=>{dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId,step,label,...values});return '처리 결과를 기록했습니다.';});
    else if (step === 'confirm-discrepancy') openModal('선적 차이 확인','<label class="field"><span>차이 확인 사유</span><textarea name="reason" required placeholder="공장 회신을 확인한 사유"></textarea></label>',values=>{dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId,step,label,reason:values.reason});return '차이를 확인했습니다.';});
    else attempt(()=>{dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId,step,label});return `${label} — 데모 반영 완료`;});
  }
  if (action === 'save-qp') saveQp(parseRoute().id);
  if (action === 'domestic-followup') openModal('납품 후속처리','<label class="field"><span>ERP 실적 등록번호</span><input name="erpNumber" required></label><label class="check-label"><input type="checkbox" required> 납품서와 구매팀 발신 초안을 확인했습니다.</label>',values=>{dispatch({type:'DOMESTIC_FOLLOWUP_COMPLETED',orderId:parseRoute().id,...values});return '납품 후속처리를 완료했습니다.';});
  if (action === 'add-delivery' || action === 'edit-delivery') openModal(action==='add-delivery'?'분할 회차 추가':'납품 예정일 변경',`<label class="field"><span>예정일</span><input type="date" name="date" required value="2026-10-20"></label>${action==='add-delivery'?'<label class="field"><span>새 회차 분할수량</span><input name="quantity" type="number" min="1" required></label>':'<label class="field"><span>변경 사유</span><textarea name="reason" required></textarea></label>'}`,values=>{dispatch({type:action==='add-delivery'?'DELIVERY_ROUND_ADDED':'DELIVERY_SCHEDULE_CHANGED',orderId:parseRoute().id,...values});return '납품 일정을 기록했습니다.';});
  if (action === 'review-duplicate') openModal('동일 파일 중복 차단','<p>동일 고객사·PO 번호·파일내용으로 등록된 업무가 있습니다.</p><p>파일 해시: 8d41…a0c2 · 기존 업무 BJ-10241</p><p class="dialog-error">중복 업무 생성이 차단되었습니다.</p>',null);
  if (action === 'review-revision') {
    const order=getState().orders['BJ-10241'];
    openModal('부분납품 후 수정본 비교',`<table><thead><tr><th>항목</th><th>기존</th><th>수정본</th></tr></thead><tbody><tr><td>PO 수량</td><td>${order.quantity}</td><td>12,000 EA</td></tr><tr><td>이미 납품 · 잠금</td><td>${order.deliveredQuantity}</td><td>${order.deliveredQuantity} EA</td></tr><tr><td>미납품 잔량</td><td>${order.quantity-order.deliveredQuantity}</td><td>${12000-order.deliveredQuantity} EA</td></tr></tbody></table><label class="field"><span>승인할 PO 총수량</span><input name="quantity" type="number" min="${order.deliveredQuantity}" required value="12000"></label><label class="field"><span>처리</span><select name="decision"><option value="approve">수정본 승인</option><option value="reject">반려</option><option value="keep">원본 유지</option></select></label>`,values=>{if(values.decision==='approve') dispatch({type:'REVISION_APPROVED',orderId:order.id,quantity:values.quantity});return values.decision==='approve'?'수정본을 승인했습니다. 납품 실적은 보존됩니다.':'기존 원본을 유지했습니다.';});
  }
  if (action === 'manual-link') {
    const order=getState().orders[parseRoute().id];
    const qy=[order.qyNumber,'QY261014-41CHVN(VSL)']; const qp=[order.qpNumber,'QP-DEMO-SPLIT'];
    openModal('QY / QP 다대다 연결',`<p class="muted">직접 연결할 문서를 선택하세요. 추가 문서는 분할·합산 연결 체험용 샘플입니다.</p><h3>QY 목록</h3>${qy.map((number,i)=>`<label class="check-label"><input type="checkbox" name="qy${i}" value="${escapeHtml(number)}" ${i===0?'checked':''}>${escapeHtml(number)}</label>`).join('')}<h3>QP 목록</h3>${qp.map((number,i)=>`<label class="check-label"><input type="checkbox" name="qp${i}" value="${escapeHtml(number)}" ${i===0?'checked':''}>${escapeHtml(number)}</label>`).join('')}`,values=>{dispatch({type:'QY_LINK_CONFIRMED',orderId:order.id,qy:Object.entries(values).filter(([key])=>key.startsWith('qy')).map(([,value])=>value),qp:Object.entries(values).filter(([key])=>key.startsWith('qp')).map(([,value])=>value)});return '선택한 QY / QP 연결을 확정했습니다.';});
  }
  if (action === 'resolve-exception') openModal('예외 조치','<label class="field"><span>조치 사유</span><textarea name="reason" required></textarea></label>',values=>{dispatch({type:'EXCEPTION_RESOLVED',id:'EX-003',reason:values.reason});return '예외 조치를 기록했습니다.';});
  if (action === 'mock-mail') openModal('발신 초안 확인','<p>수신자 그룹: CHEMTRO VINA Shipping Team</p><p>첨부: QY261013-40CHVN(VSL).xlsx</p><label class="check-label"><input type="checkbox" required> 수신자와 고객용 첨부를 확인했습니다.</label>',()=> '발신 초안 검토를 완료했습니다.');
  if (action === 'mock-master-add' || action === 'mock-master-edit') openModal('기준정보 편집','<label class="field"><span>표시명</span><input name="name" required placeholder="기준정보 표시명"></label><label class="field"><span>업무 코드</span><input name="code" required placeholder="CHVN"></label>',()=> '기준정보 편집 예시를 확인했습니다.');
  if (action === 'copy-row' || action === 'copy-all') copyRows(action === 'copy-row' ? Number(event.target.closest('[data-row]').dataset.row) : null);
  const region = event.target.closest('[data-field-region]');
  if (region) {const field=getState().poReview.fields.find(field=>field.regionId===region.dataset.fieldRegion);if(field) dispatch({type:'FIELD_SELECTED',field:field.key});}
});
document.addEventListener('input', event => {
  if (event.target.matches('[data-filter="search"]')) dispatch({ type: 'FILTER_CHANGED', filters: { search: event.target.value } });
});
document.addEventListener('change', event => {
  if (event.target.matches('select[data-filter]')) dispatch({ type: 'FILTER_CHANGED', filters: { [event.target.dataset.filter]: event.target.value } });
  if (event.target.matches('[data-scenario]') && event.target.value) dispatch({type:'SCENARIO_CHANGED',orderId:parseRoute().id,scenario:event.target.value});
});

function attempt(callback) {
  try {const message=callback();if(message) showToast(message);} catch(error) {showToast(error.message);}
}

function saveQp(orderId) {
  attempt(()=>{const values=Object.fromEntries(new FormData(document.querySelector('#qp-form')));dispatch({type:'QP_RECORDED',orderId,values});return 'QP·선적정보를 저장했습니다.';});
}

function openModal(title, body, onSave) {
  document.querySelector('#workflow-dialog')?.remove();
  const previous = document.activeElement;
  const dialog = document.createElement('dialog');
  dialog.id = 'workflow-dialog'; dialog.className = 'workflow-dialog';
  dialog.innerHTML = `<form><header><h2 id="dialog-title">${escapeHtml(title)}</h2><button type="button" data-close aria-label="닫기">×</button></header><div class="dialog-body">${body}<p class="dialog-error" role="alert"></p></div><footer><button type="button" class="button button--ghost" data-close>닫기</button>${onSave ? '<button class="button button--primary" type="submit">확인</button>' : ''}</footer></form>`;
  dialog.setAttribute('aria-labelledby','dialog-title');
  document.body.append(dialog);
  const close=()=>{dialog.close();dialog.remove();if(previous?.isConnected) previous.focus();};
  dialog.querySelectorAll('[data-close]').forEach(button=>button.addEventListener('click',close));
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  dialog.querySelector('form').addEventListener('submit',event=>{event.preventDefault();try {const message=onSave?.(Object.fromEntries(new FormData(event.currentTarget)));close();if(message) showToast(message);} catch(error) {dialog.querySelector('.dialog-error').textContent=error.message;}});
  dialog.showModal();
}

async function copyRows(index) {
  const rows=selectExcelRows(getState()).map(row=>[row.owner,row.customer,row.model,row.currency,row.price,row.date,row.quantity].join('\t'));
  const text=(index===null?rows:[rows[index]]).join('\n');
  try {await navigator.clipboard.writeText(text);showToast(index===null?'전체 행을 복사했습니다.':'선택한 행을 복사했습니다.');}
  catch {openModal('복사할 데이터',`<label class="field"><span>아래 값을 선택하여 복사하세요.</span><textarea readonly rows="6">${escapeHtml(text)}</textarea></label>`,null);}
}
subscribe(render);
if (!location.hash) location.hash = '#/';
render();

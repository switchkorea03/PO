import test from 'node:test';
import assert from 'node:assert/strict';
import { dispatch, filterOrders, getState, resetDemo, seedState, selectPriorityWork } from '../dist/assets/store.js';
import { renderDashboard } from '../dist/assets/screens/dashboard.js';
import { renderOrders } from '../dist/assets/screens/orders.js';

test('reset restores seeded delivery quantity without retaining mutated references', () => {
  resetDemo();
  const before = getState();
  dispatch({ type: 'DELIVERY_CONFIRMED', orderId: 'BJ-10241', quantity: 2000 });
  assert.equal(getState().orders['BJ-10241'].deliveredQuantity, 8000);
  resetDemo();
  assert.equal(getState().orders['BJ-10241'].deliveredQuantity, 6000);
  assert.notEqual(getState(), before);
});

test('dashboard shows blocked and due-today work before later work', () => {
  assert.deepEqual(selectPriorityWork(seedState).map(item => item.id).slice(0, 2), ['EX-003', 'BJ-10241']);
});

test('order filter combines owner, type, and status', () => {
  const result = filterOrders(seedState.orders, {
    owner: '김영업', type: 'overseas', status: 'shipment-ready'
  });
  assert.deepEqual(result.map(order => order.id), ['CV-8821']);
});

test('order search checks customer, PO number, model, and work ID', () => {
  assert.deepEqual(filterOrders(seedState.orders, { search: '세림' }).map(order => order.id), ['SE-2408']);
});

test('dashboard and order list expose their primary work controls', () => {
  assert.match(renderDashboard(seedState), /우선 처리 업무/);
  assert.match(renderOrders(seedState, seedState.filters), /PO 검색/);
});

test('delivery confirmation updates the pending round and rejects invalid or repeat submissions', () => {
  resetDemo();
  assert.throws(() => dispatch({type:'DELIVERY_CONFIRMED',orderId:'BJ-10241',quantity:-1}), /수량/);
  dispatch({type:'DELIVERY_CONFIRMED',orderId:'BJ-10241',quantity:4000});
  assert.equal(getState().orders['BJ-10241'].deliveries[1].actual,4000);
  assert.throws(() => dispatch({type:'DELIVERY_CONFIRMED',orderId:'BJ-10241',quantity:1}), /수량|완료/);
});

test('review approval initializes domestic detail and advances its status', () => {
  resetDemo();
  dispatch({type:'FIELD_CONFIRMED',field:'quantity',value:'2,500 EA'});
  dispatch({type:'FIELD_CONFIRMED',field:'unitPrice',value:'₩12,800'});
  dispatch({type:'REVIEW_CONFIRMED',orderId:'SE-2408'});
  assert.equal(getState().orders['SE-2408'].status,'registered');
  assert.ok(Array.isArray(getState().orders['SE-2408'].deliveries));
});

test('overseas reducer blocks out-of-order transitions when UI is bypassed', () => {
  resetDemo();
  assert.throws(() => dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId:'CV-8821',step:'internal-mail'}), /순서/);
  assert.equal(getState().orders['CV-8821'].internalMailSent,undefined);
});

test('QP save retains entered values and detects quantity discrepancy', () => {
  resetDemo();
  dispatch({type:'QP_RECORDED',orderId:'CV-8821',values:{qpNumber:'QP-USER-01',onBoard:'2026-10-16',etd:'2026-10-17',eta:'',etaStatus:'미정',actualQuantity:3900}});
  assert.equal(getState().orders['CV-8821'].qpNumber,'QP-USER-01');
  assert.equal(getState().orders['CV-8821'].discrepancy,true);
  assert.throws(() => dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId:'CV-8821',step:'confirm-qy-link'}), /순서/);
});

test('completed correction creates a record without changing original quantity', () => {
  resetDemo();
  for(const step of ['confirm-qy-link','customer-mail','import-register','receipt','internal-mail']) dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId:'CV-8821',step});
  dispatch({type:'CORRECTION_CREATED',orderId:'CV-8821',quantity:3900,reason:'현장 확인'});
  assert.equal(getState().orders['CV-8821'].actualQuantity,4000);
  assert.equal(getState().corrections[0].after.actualQuantity,3900);
});

test('any ON BOARD and ETD difference requires explicit confirmation', () => {
  resetDemo();
  dispatch({type:'QP_RECORDED',orderId:'CV-8821',values:{qpNumber:'QP-DATE',onBoard:'2026-10-16',etd:'2026-10-17',eta:'2026-10-22',etaStatus:'확정',actualQuantity:4000}});
  assert.equal(getState().orders['CV-8821'].discrepancy,true);
});

test('approved review copies user-corrected quantity and price to the actual order', () => {
  resetDemo();
  dispatch({type:'FIELD_CONFIRMED',field:'quantity',value:'2,700 EA'});
  dispatch({type:'FIELD_CONFIRMED',field:'unitPrice',value:'₩13,000'});
  dispatch({type:'REVIEW_CONFIRMED',orderId:'SE-2408'});
  assert.equal(getState().orders['SE-2408'].quantity,2700);
  assert.equal(getState().orders['SE-2408'].unitPrice,13000);
});

test('completed production is immutable and revision cannot reduce already delivered quantity', () => {
  resetDemo();
  dispatch({type:'DELIVERY_CONFIRMED',orderId:'BJ-10241',quantity:4000});
  assert.throws(()=>dispatch({type:'PRODUCTION_APPROVED',orderId:'BJ-10241',quantity:2000}),/완료/);
  resetDemo();
  assert.throws(()=>dispatch({type:'REVISION_APPROVED',orderId:'BJ-10241',quantity:5000}),/이미 납품/);
  dispatch({type:'REVISION_APPROVED',orderId:'BJ-10241',quantity:12000});
  assert.equal(getState().orders['BJ-10241'].deliveredQuantity,6000);
  assert.equal(getState().orders['BJ-10241'].quantity,12000);
});

test('manual multi-link confirmation requires both QY and QP selections', () => {
  resetDemo();
  assert.throws(()=>dispatch({type:'QY_LINK_CONFIRMED',orderId:'CV-8821',qy:[],qp:[]}),/선택/);
  dispatch({type:'QY_LINK_CONFIRMED',orderId:'CV-8821',qy:['QY261013-40CHVN(VSL)','QY261014-41CHVN(VSL)'],qp:['QP-A','QP-B']});
  assert.equal(getState().orders['CV-8821'].links.qy.length,2);
  assert.equal(getState().orders['CV-8821'].qyLinkConfirmed,true);
});

test('short shipment retains residual quantity after all follow-up steps', () => {
  resetDemo();
  dispatch({type:'QP_RECORDED',orderId:'CV-8821',values:{qpNumber:'QP-PARTIAL',onBoard:'2026-10-17',etd:'2026-10-17',actualQuantity:3900,etaStatus:'미정',eta:''}});
  dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId:'CV-8821',step:'confirm-discrepancy',reason:'부분선적 확인'});
  for (const step of ['confirm-qy-link','customer-mail','import-register','receipt','internal-mail']) dispatch({type:'OVERSEAS_STEP_COMPLETED',orderId:'CV-8821',step});
  assert.notEqual(getState().orders['CV-8821'].status,'complete');
  assert.equal(getState().orders['CV-8821'].remainingQuantity,100);
});

test('splitting pending schedule preserves quantity and confirms only its first round', () => {
  resetDemo();
  dispatch({type:'DELIVERY_ROUND_ADDED',orderId:'BJ-10241',quantity:1000,date:'2026-10-20'});
  assert.deepEqual(getState().orders['BJ-10241'].deliveries.filter(row=>row.actual===null).map(row=>row.planned),[3000,1000]);
  dispatch({type:'DELIVERY_CONFIRMED',orderId:'BJ-10241',quantity:3000,date:'2026-10-15'});
  assert.equal(getState().orders['BJ-10241'].deliveries.length,3);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { seedState } from '../dist/assets/store.js';
import { selectSourceRegion, renderPoReview } from '../dist/assets/screens/po-review.js';
import { approveProduction, confirmDelivery, renderDomestic } from '../dist/assets/screens/domestic.js';
import { renderOrderDetail } from '../dist/assets/screens/order-detail.js';

test('field selection links the extracted value to its source region', () => {
  assert.equal(selectSourceRegion(seedState.poReview, 'quantity').id, 'pdf-region-quantity');
});

test('delivery confirmation rejects a total above the ordered quantity', () => {
  assert.throws(() => confirmDelivery(seedState.orders['BJ-10241'], 7000), /PO 수량을 초과/);
});

test('production approval uses only the quantity entered by the user', () => {
  assert.deepEqual(approveProduction({ enteredQuantity: 5000, stock: 3500 }), { quantity: 5000, approved: true });
});

test('review and domestic detail expose linked review and delivery actions', () => {
  assert.match(renderPoReview(seedState), /원본과 추출값 연결 검토/);
  assert.match(renderDomestic(seedState.orders['BJ-10241']), /실제 납품수량/);
  assert.match(renderOrderDetail(seedState.orders['BJ-10241']), /분할납품 진행/);
});

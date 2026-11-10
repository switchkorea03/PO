import test from 'node:test';
import assert from 'node:assert/strict';
import { formatQyNumber, canAdvanceOverseas, suggestQyLinks, renderOverseas } from '../dist/assets/screens/overseas.js';
import { seedState } from '../dist/assets/store.js';

test('validated QY number uses the original date, sequence, customer, and mode rule', () => {
  assert.equal(formatQyNumber({ exw: '2026-10-13', sequence: 40, customerCode: 'CHVN', mode: 'VSL' }), 'QY261013-40CHVN(VSL)');
});

test('QP entry cannot be reached before QY sending and factory confirmation', () => {
  assert.equal(canAdvanceOverseas({ stage: 'qy-draft' }).next, 'send-qy');
  assert.equal(canAdvanceOverseas({ stage: 'qy-sent', qySent: true }).next, 'confirm-factory-reply');
});

test('quantity or date discrepancy locks customer and ERP follow-up', () => {
  assert.equal(canAdvanceOverseas({ stage: 'qp-recorded', discrepancy: true, discrepancyConfirmed: false }).blocked, true);
});

test('QY suggestions use shipment facts rather than a QP suffix', () => {
  const suggestions = suggestQyLinks({ actualQuantity: 4000, exw: '2026-10-13' }, [
    { number: 'QY261013-40CHVN(VSL)', quantity: 4000, exw: '2026-10-13' },
    { number: 'QY261014-41CHVN(VSL)', quantity: 3500, exw: '2026-10-14' }
  ]);
  assert.deepEqual(suggestions.map(item => item.number), ['QY261013-40CHVN(VSL)']);
});

test('overseas detail keeps the corrected business sequence visible', () => {
  const html = renderOverseas(seedState.orders['CV-8821']);
  assert.ok(html.indexOf('QY 생성·발송') < html.indexOf('중국 공장 회신'));
  assert.ok(html.indexOf('중국 공장 회신') < html.indexOf('QP·선적정보 입력'));
});

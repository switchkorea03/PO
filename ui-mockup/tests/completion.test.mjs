import test from 'node:test';
import assert from 'node:assert/strict';
import { canCompleteOrder, createCorrection, renderOperations, selectExcelRows } from '../dist/assets/screens/operations.js';
import { renderMasterData } from '../dist/assets/screens/master-data.js';
import { seedState } from '../dist/assets/store.js';

const completeOrder = {
  id: 'CV-8821', actualQuantity: 4000, customerMailSent: true,
  importRegistered: true, receiptRecorded: true, internalMailSent: true
};

test('Excel copy is optional and never blocks order completion', () => {
  assert.equal(canCompleteOrder({ ...completeOrder, excelCopied: false }), true);
});

test('correction preserves the immutable original and records before, after, and reason', () => {
  const result = createCorrection(completeOrder, { actualQuantity: 3900 }, '현장 수량 정정');
  assert.equal(result.original.actualQuantity, 4000);
  assert.equal(result.correction.before.actualQuantity, 4000);
  assert.equal(result.correction.after.actualQuantity, 3900);
  assert.equal(result.correction.reason, '현장 수량 정정');
});

test('operations and master screens expose safe mock-only controls', () => {
  assert.match(renderOperations({ section: 'mail' }, seedState), /Outlook 초안/);
  assert.match(renderOperations({ section: 'excel' }, seedState), /Excel 복사/);
  assert.match(renderMasterData(seedState), /수신자 그룹/);
});

test('Excel excludes planned-only orders and copies confirmed delivery date and quantity', () => {
  const rows = selectExcelRows(seedState);
  assert.equal(rows.length,1);
  assert.equal(rows[0].quantity,6000);
  assert.equal(rows[0].date,'2026-10-07');
});

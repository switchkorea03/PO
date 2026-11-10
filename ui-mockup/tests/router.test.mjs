import test from 'node:test';
import assert from 'node:assert/strict';
import { parseRoute } from '../dist/assets/router.js';

test('domestic order URL opens the matching detail screen', () => {
  assert.deepEqual(parseRoute('#/orders/BJ-10241'), {
    screen: 'order-detail',
    id: 'BJ-10241'
  });
});

test('query values are decoded and available to list screens', () => {
  assert.deepEqual(parseRoute('#/orders?type=overseas&owner=%EA%B9%80%EC%98%81%EC%97%85'), {
    screen: 'orders',
    query: { type: 'overseas', owner: '김영업' }
  });
});

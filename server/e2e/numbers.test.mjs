import test from 'node:test';
import assert from 'node:assert/strict';
import {groupDigits} from '../static/po/numbers.js';
test('groups only integer digits and preserves precise fractional digits',()=>{
 assert.equal(groupDigits('12345.678901'),'12,345.678901');
 assert.equal(groupDigits('12345678901234567890.1234567890'),'12,345,678,901,234,567,890.1234567890');
});

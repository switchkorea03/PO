import test from 'node:test';
import assert from 'node:assert/strict';
import {nextWeekTuesday, buildEvents} from '../dist/schedule.js';

test('next-week Tuesday follows calendar weeks rather than the nearest Tuesday',()=>{
  for(const [date,expected] of [['2026-10-13','2026-10-20'],['2026-10-18','2026-10-20'],['2026-10-19','2026-10-27']]) assert.equal(nextWeekTuesday(date),expected);
});
test('domestic dates use shipping date offsets and preserve a separate due date',()=>{
  const events=buildEvents({id:'PO1',type:'domestic',shipDate:'2026-11-01',dueDate:'2026-11-03'});
  assert.deepEqual(events.map(e=>e.date),['2026-10-30','2026-10-31','2026-11-03']);
});
test('overseas missing ETA retains an undated task and updates it without duplicates',()=>{
  const order={id:'PO2',type:'overseas',receivedDate:'2026-10-13',eta:''};
  assert.deepEqual(buildEvents(order).map(e=>e.date),['2026-10-13','2026-10-13','2026-10-20','']);
  assert.deepEqual(buildEvents({...order,eta:'2026-10-31'}).map(e=>e.date),['2026-10-13','2026-10-13','2026-10-20','2026-11-01']);
});

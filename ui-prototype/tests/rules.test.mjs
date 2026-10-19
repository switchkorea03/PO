import test from 'node:test';
import assert from 'node:assert/strict';
import {previousWeekday,nextTuesday,followup,remaining,validateAllocation} from '../dist/rules.js';
test('Monday shipment preparation falls on Friday',()=>assert.equal(previousWeekday('2026-10-19'),'2026-10-16'));
test('Sunday receipt uses original week for next Tuesday',()=>assert.equal(nextTuesday('2026-10-18'),'2026-10-20'));
test('Friday and weekend ETDs follow up on Monday; unknown stays undated',()=>{for(const d of ['2026-10-16','2026-10-17','2026-10-18'])assert.equal(followup(d),'2026-10-19');assert.equal(followup(null),null);});
test('Only completed shipments count toward shipped quantity',()=>assert.equal(remaining(100,[{qty:70,done:true},{qty:30,done:false}],0),30));
test('Allocation rejects exceeding order and retains cancellation',()=>{assert.equal(validateAllocation(100,[70,30],0),true);assert.equal(validateAllocation(100,[70,40],0),false);assert.equal(validateAllocation(100,[70,20],20),false);});

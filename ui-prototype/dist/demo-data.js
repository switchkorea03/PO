import {reconcile} from './rules.js';
export const DEMO_TODAY='2026-10-19';
export function freshState(){
 const state={version:1,orders:[
  {id:'bj',customer:'범진전자',type:'domestic',po:'BJ-2610-01',received:'2026-10-12',contact:'구매팀 김담당',currency:'USD',code:'MESAH-001',name:'TACT SWITCH · JTP1280A6',qty:100,unit:'EA',price:'0.0145',due:'2026-10-19',cancelledQty:0,shipments:[{id:'s1',qty:70,date:'2026-10-19',done:true},{id:'s2',qty:30,date:'2026-10-23',done:false}],history:['10.19 08:40 · 김담당 · 1차 70 EA 출고 완료','10.16 16:10 · 김담당 · 2차 30 EA 분할출고 추가']},
  {id:'hb',customer:'한빛테크',type:'domestic',po:'HB-2610-08',received:'2026-10-15',contact:'자재팀 이담당',currency:'KRW',code:'CAP-205',name:'세라믹 커패시터',qty:200,unit:'EA',price:'125',due:'2026-10-19',cancelledQty:0,shipments:[{id:'s1',qty:200,date:'2026-10-19',done:false}],history:['10.15 14:20 · 김담당 · PO 등록']},
  {id:'vn',customer:'비나일렉트로닉스',type:'overseas',po:'VN-2610-03',received:'2026-10-18',contact:'Purchasing · Linh',currency:'USD',code:'CON-100',name:'BOARD CONNECTOR',qty:1200,unit:'PCS',price:'0.25',due:'2026-11-10',cancelledQty:0,shipments:[{id:'s1',qty:1200,etd:null,eta:null,done:false}],history:['10.19 08:30 · 김담당 · 실제 PO 수령일 10.18 확인']},
  {id:'ap',customer:'알파컴포넌트',type:'overseas',po:'AP-2610-02',received:'2026-10-08',contact:'Buyer · Alex',currency:'USD',code:'IC-880',name:'POWER MANAGEMENT IC',qty:500,unit:'EA',price:'1.80',due:'2026-10-30',cancelledQty:0,shipments:[{id:'s1',qty:500,etd:'2026-10-16',eta:'2026-10-24',done:true}],history:['10.16 15:20 · 김담당 · 선적 완료 / ETA 기록']}
 ],tasks:[],notice:{enabled:true,recipient:'010-0000-0000',sender:'02-000-0000'},history:[{id:'n1',at:'2026-10-19 09:00',kind:'정기 알림',status:'전달 완료',count:9,attempt:1},{id:'n2',at:'2026-10-16 09:15',kind:'정기 알림',status:'최종 실패',count:2,attempt:4},{id:'n3',at:'2026-10-15 11:20',kind:'추가 알림',status:'결과 확인 중',count:1,attempt:1}]};
 reconcile(state);
 for(const t of state.tasks){if(t.order==='bj'&&t.shipment==='s1'&&['share','request'].includes(t.kind))t.steps.forEach(s=>s.done=true);if(t.order==='ap'&&['invoice','bl'].includes(t.kind))t.steps.forEach(s=>s.done=true);}
 state.tasks.find(t=>t.order==='ap'&&t.kind==='erp').steps[0].done=true;
 state.tasks.find(t=>t.order==='hb'&&t.kind==='request').steps[0].done=true;
 state.tasks.find(t=>t.order==='bj'&&t.kind==='request'&&t.shipment==='s1').review=true;
 return state;
}

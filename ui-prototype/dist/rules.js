const date=s=>new Date(s+'T12:00:00Z');
const iso=d=>d.toISOString().slice(0,10);
export const shift=(s,n)=>{const d=date(s);d.setUTCDate(d.getUTCDate()+n);return iso(d);};
export const weekday=s=>date(s).getUTCDay();
export const nextWeekday=s=>{while([0,6].includes(weekday(s)))s=shift(s,1);return s;};
export const previousWeekday=s=>{s=shift(s,-1);while([0,6].includes(weekday(s)))s=shift(s,-1);return s;};
export const nextTuesday=s=>shift(s,8-((weekday(s)+6)%7));
export const followup=s=>s?nextWeekday(shift(s,1)):null;
export const remaining=(ordered,shipments,cancelled=0)=>ordered-shipments.filter(s=>s.done&&!s.cancelled).reduce((n,s)=>n+s.qty,0)-cancelled;
export const validateAllocation=(ordered,quantities,cancelled=0)=>quantities.every(q=>Number.isFinite(q)&&q>0)&&quantities.reduce((n,q)=>n+q,0)+cancelled<=ordered;
export const catalog={
 share:['출고 내역 공유',['출고품·수량·출고일을 고객에게 메일 전달']],
 request:['의뢰서(ERP)+명세서(PDF) 전달',['거래명세서 PDF 저장·인쇄','출고의뢰 등록·인쇄','명세서·의뢰서를 구매팀에 전달']],
 statement:['명세서 공유',['거래명세서 PDF를 고객에게 전달']],
 excel:['엑셀 기입',['출하계획 Excel에 수량 입력']],
 voucher:['전표 인쇄',['출고전표 인쇄','전표를 반으로 잘라 지정 바구니에 전달']],
 invoice:['인보이스+ERP',['인보이스 작성·중국 공장 전달','ERP 주문등록(수출)']],
 bl:['BL, ETA 고객 공유',['BL 서류를 고객에게 전달','ETA를 고객에게 안내']],
 erp:['ERP 2개 처리',['수입선적등록(수입)','입고처리(수입)']],
 mail:['출고 메일',['중계무역 출고메일을 내부 영업관리팀에 공유']]
};
export function reconcile(state){
 const previous=new Map(state.tasks.map(t=>[t.id,t]));const tasks=[];
 for(const o of state.orders){
  const add=(kind,s,auto)=>{
   const id=o.id+':'+(s?.id||'po')+':'+kind;const old=previous.get(id);const [title,steps]=catalog[kind];
   const labels=steps.map(label=>kind==='request'&&label==='출고의뢰 등록·인쇄'?`${o.currency==='USD'?'출고의뢰등록(수출)':'출고의뢰등록'}: 등록·인쇄`:kind==='voucher'&&label==='출고전표 인쇄'?`${o.currency==='USD'?'거래명세서(수출)':'출고처리'}: 전표 인쇄`:label);
   const task={id,order:o.id,shipment:s?.id,kind,title,auto,manual:null,date:auto,steps:labels.map(label=>({label,done:false})),review:false,cancelled:!!(o.cancelled||s?.cancelled)};
   if(old){const done=old.steps.every(v=>v.done);Object.assign(task,{manual:old.manual,steps:old.steps,review:old.review,completed:old.completed});task.recalc=!!old.manual&&old.auto!==auto;task.date=done?old.date:auto?(old.manual||auto):null;task.review=old.review||(done&&(old.auto!==auto||task.cancelled));if(done)task.cancelled=false;}
   tasks.push(task);
  };
  if(o.type==='overseas'){add('invoice',null,nextWeekday(o.received));add('bl',null,nextTuesday(o.received));}
  for(const s of o.shipments){
   if(o.type==='domestic'){for(const k of ['share','request'])add(k,s,previousWeekday(s.date));for(const k of ['statement','excel','voucher'])add(k,s,s.date);}
   else for(const k of ['erp','mail','excel'])add(k,s,followup(s.etd));
  }
 }
 state.tasks=tasks;
}

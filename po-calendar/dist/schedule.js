const DAY=86400000;
export const defaultRules = [
  {id:'domestic-d2',type:'domestic',basis:'출고 2일 전',title:'출고서류·재고 확인'},
  {id:'domestic-d1',type:'domestic',basis:'출고 1일 전',title:'출고 준비 최종 확인'},
  {id:'domestic-due',type:'domestic',basis:'납기일',title:'납기일'},
  {id:'overseas-received',type:'overseas',basis:'PO 수령일',title:'PO 수령'},
  {id:'overseas-day',type:'overseas',basis:'PO 수령 당일',title:'PO 내용 확인·등록'},
  {id:'overseas-tuesday',type:'overseas',basis:'다음주 화요일',title:'발주·선적 일정 확인'},
  {id:'overseas-eta',type:'overseas',basis:'ETA 다음날',title:'입고·수입 처리 확인'}
];
export function dateValue(value){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value||'')) throw new Error('날짜를 확인하세요.');
  const date=new Date(value+'T00:00:00Z');
  if(!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==value) throw new Error('유효한 날짜를 입력하세요.');
  return date;
}
export function addDays(value,offset){const date=dateValue(value);return new Date(date.getTime()+offset*DAY).toISOString().slice(0,10);}
export function nextWeekTuesday(value){const date=dateValue(value);const sinceMonday=(date.getUTCDay()+6)%7;return addDays(value,8-sinceMonday);}
export function buildEvents(order,rules=defaultRules){
  const dates=order.type==='domestic'?{
    'domestic-d2':order.shipDate?addDays(order.shipDate,-2):'',
    'domestic-d1':order.shipDate?addDays(order.shipDate,-1):'',
    'domestic-due':order.dueDate||''
  }:{
    'overseas-received':order.receivedDate||'',
    'overseas-day':order.receivedDate||'',
    'overseas-tuesday':order.receivedDate?nextWeekTuesday(order.receivedDate):'',
    'overseas-eta':order.eta?addDays(order.eta,1):''
  };
  return rules.filter(rule=>rule.type===order.type).map(rule=>({...rule,eventId:`${order.id}:${rule.id}`,orderId:order.id,customer:order.customer,date:dates[rule.id]||''}));
}

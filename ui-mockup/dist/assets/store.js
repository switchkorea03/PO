import { canAdvanceOverseas, formatQyNumber } from './screens/overseas.js';
import { confirmDelivery, approveProduction } from './screens/domestic.js';
import { createCorrection } from './screens/operations.js';

const createSeedState = () => ({
  currentRole: '영업 담당자',
  filters: { search: '', owner: '전체', type: 'all', status: 'all' },
  selectedField: 'quantity',
  toast: null,
  orders: {
    'BJ-10241': {
      id: 'BJ-10241', poNumber: 'PO-2026-1013-07', customer: '범진전자', owner: '김영업',
      type: 'domestic', typeLabel: '국내', model: 'BCM-24A', quantity: 10000,
      deliveredQuantity: 6000, dueDate: '2026-10-13', status: 'delivery', statusLabel: '분할납품 진행',
      priority: 2, stock: 3500, productionQuantity: null, productionDueDate: '2026-10-27',
      deliveries: [
        { round: 1, date: '2026-10-07', planned: 6000, actual: 6000, status: '완료' },
        { round: 2, date: '2026-10-15', planned: 4000, actual: null, status: '예정' }
      ],
      milestones: ['PO 확인', 'iCUBE 등록', '생산·재고', '납품 진행', '완료'], currentStep: 3,
      audit: [
        { at: '10.13 09:42', actor: '김영업', text: '2차 납품 예정일을 확인했습니다.' },
        { at: '10.12 16:10', actor: '시스템', text: '1차 납품 실적 6,000 EA가 반영되었습니다.' }
      ]
    },
    'CV-8821': {
      id: 'CV-8821', poNumber: 'PO-CV-261013', customer: 'CHEMTRO VINA', owner: '김영업',
      type: 'overseas', typeLabel: '해외', model: 'CH-88V', quantity: 4000,
      deliveredQuantity: 0, dueDate: '2026-10-14', exw: '2026-10-13', status: 'shipment-ready',
      statusLabel: 'QP 연결 확인', priority: 3, mode: 'VSL', customerCode: 'CHVN', sequence: 40,
      qyNumber: 'QY261013-40CHVN(VSL)', qpNumber: 'QP1026-CHVN35', actualQuantity: 4000,
      onBoard: '2026-10-17', etd: '2026-10-17', eta: '2026-10-22', stage: 'qp-recorded',
      qySent: true, factoryReplyConfirmed: true, qyLinkConfirmed: false, discrepancyConfirmed: false,
      milestones: ['PO 확인', 'QY 발송', '공장 회신', 'QP 연결', '후속 처리', '완료'], currentStep: 3,
      audit: [
        { at: '10.13 11:18', actor: '김영업', text: 'QP·선적정보를 수동 입력했습니다.' },
        { at: '10.13 09:05', actor: '김영업', text: '중국 공장 회신을 확인했습니다.' }
      ]
    },
    'SE-2408': {
      id: 'SE-2408', poNumber: 'PO-2026-1012-11', customer: '세림모터스', owner: '박해외',
      type: 'domestic', typeLabel: '국내', model: 'SM-402', quantity: 2500,
      deliveredQuantity: 0, dueDate: '2026-10-14', status: 'review', statusLabel: 'PO 검토 필요',
      stock: 800, productionQuantity: null, productionDueDate: '2026-10-27',
      deliveries: [{round:1,date:'2026-10-14',planned:2500,actual:null,status:'예정'}],
      priority: 5, milestones: ['PO 확인', 'iCUBE 등록', '생산·재고', '납품 진행', '완료'], currentStep: 0,
      audit: []
    }
  },
  priorityItems: [
    { id: 'EX-003', kind: 'exception', title: '단가 불일치 확인', subtitle: 'CHEMTRO VINA · CH-88V', due: '오늘', severity: 'danger', href: '#/operations/exceptions' },
    { id: 'BJ-10241', kind: 'order', title: '2차 납품 수량 확정', subtitle: '범진전자 · BCM-24A', due: '오늘 15:00', severity: 'warning', href: '#/orders/BJ-10241' },
    { id: 'CV-8821', kind: 'order', title: 'QY 연결 확정', subtitle: 'CHEMTRO VINA · QP1026-CHVN35', due: '내일', severity: 'info', href: '#/orders/CV-8821' }
  ],
  poReview: {
    id: 'SE-2408', fileName: 'PO_세림모터스_20261012.pdf', confidence: 84,
    fields: [
      { key: 'poNumber', label: 'PO 번호', value: 'PO-2026-1012-11', confidence: 98, regionId: 'pdf-region-po' },
      { key: 'model', label: '모델', value: 'SM-402', confidence: 93, regionId: 'pdf-region-model' },
      { key: 'quantity', label: '수량', value: '2,500 EA', confidence: 76, regionId: 'pdf-region-quantity' },
      { key: 'unitPrice', label: '단가', value: '₩12,800', confidence: 69, regionId: 'pdf-region-price' },
      { key: 'dueDate', label: '납기', value: '2026-10-14', confidence: 88, regionId: 'pdf-region-due' }
    ],
    regions: [
      { id: 'pdf-region-po', label: 'PO 번호', x: 62, y: 13, w: 29, h: 7 },
      { id: 'pdf-region-model', label: '모델', x: 8, y: 44, w: 24, h: 7 },
      { id: 'pdf-region-quantity', label: '수량', x: 51, y: 44, w: 15, h: 7 },
      { id: 'pdf-region-price', label: '단가', x: 69, y: 44, w: 18, h: 7 },
      { id: 'pdf-region-due', label: '납기', x: 57, y: 58, w: 31, h: 7 }
    ]
  },
  exceptions: [{ id: 'EX-003', owner: '김영업', type: '단가 불일치', status: '담당자 확인 필요', orderId: 'CV-8821' }],
  corrections: []
});

export const seedState = createSeedState();
let state = structuredClone(seedState);
const listeners = new Set();
const emit = () => listeners.forEach(listener => listener(state));

export const getState = () => state;
export const subscribe = listener => { listeners.add(listener); return () => listeners.delete(listener); };
export const resetDemo = () => { state = createSeedState(); emit(); return state; };

export function selectPriorityWork(source) {
  return [...source.priorityItems].filter(item=>item.kind!=='order'||(source.orders[item.id]?.status!=='complete' && (item.id!=='CV-8821'||!source.orders[item.id]?.qyLinkConfirmed) && (item.id!=='BJ-10241'||source.orders[item.id]?.deliveredQuantity<source.orders[item.id]?.quantity))).sort((a, b) => {
    const severity = { danger: 0, warning: 1, info: 2 };
    return severity[a.severity] - severity[b.severity];
  });
}

export function filterOrders(orders, filters = {}) {
  const values = Array.isArray(orders) ? orders : Object.values(orders);
  const term = (filters.search || '').trim().toLowerCase();
  return values.filter(order =>
    (!term || [order.id, order.poNumber, order.customer, order.model].some(value => String(value).toLowerCase().includes(term))) &&
    (!filters.owner || filters.owner === '전체' || order.owner === filters.owner) &&
    (!filters.type || filters.type === 'all' || order.type === filters.type) &&
    (!filters.status || filters.status === 'all' || order.status === filters.status)
  );
}

export function dispatch(action) {
  switch (action.type) {
    case 'DELIVERY_CONFIRMED': {
      const order = state.orders[action.orderId];
      if (!order) throw new Error('주문을 찾을 수 없습니다.');
      if (order.status === 'complete') throw new Error('완료된 업무는 정정업무로 처리하세요.');
      const result = confirmDelivery(order, action.quantity);
      const pending = order.deliveries.find(row => row.actual === null);
      if (!pending) throw new Error('납품 회차를 먼저 추가하세요.');
      pending.actual = Number(action.quantity);
      pending.status = '완료';
      order.deliveredQuantity = result.deliveredQuantity;
      if (result.remainingQuantity > 0 && !order.deliveries.some(row=>row.actual===null)) order.deliveries.push({round:order.deliveries.length+1,date:pending.date,planned:result.remainingQuantity,actual:null,status:'예정'});
      else if (result.remainingQuantity === 0) { order.status = 'followup'; order.statusLabel = '납품 후속처리 대기'; }
      pending.actualDate = action.date || pending.date;
      order.audit.unshift({at:'방금',actor:order.owner,text:`실제 납품수량 ${Number(action.quantity).toLocaleString('ko-KR')} EA 확정`});
      break;
    }
    case 'FILTER_CHANGED': state.filters = { ...state.filters, ...action.filters }; break;
    case 'FIELD_SELECTED': state.selectedField = action.field; break;
    case 'FIELD_CONFIRMED': {
      const field = state.poReview.fields.find(field => field.key === action.field);
      if (!field || !String(action.value).trim()) throw new Error('필드 값을 입력하세요.');
      if (/[<>]/.test(action.value) || (['quantity','unitPrice'].includes(action.field) && /-/.test(action.value))) throw new Error('올바른 필드 값을 입력하세요.');
      field.value = String(action.value).trim(); field.confirmed = true;
      break;
    }
    case 'REVIEW_CONFIRMED': {
      if (state.poReview.fields.some(field => field.confidence < 80 && !field.confirmed)) throw new Error('수량·단가를 원본과 확인하세요.');
      const order = state.orders[action.orderId];
      const fields = Object.fromEntries(state.poReview.fields.map(field=>[field.key,field.value]));
      const quantity = Number(fields.quantity.replace(/[^0-9.]/g,''));
      const unitPrice = Number(fields.unitPrice.replace(/[^0-9.]/g,''));
      if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(unitPrice) || unitPrice <= 0) throw new Error('수량·단가를 양수로 입력하세요.');
      if (!/^\d{4}-\d{2}-\d{2}$/.test(fields.dueDate)) throw new Error('납기를 YYYY-MM-DD 형식으로 입력하세요.');
      Object.assign(order,{poNumber:fields.poNumber,model:fields.model,quantity,unitPrice,dueDate:fields.dueDate});
      order.deliveries[0].planned = quantity; order.deliveries[0].date = fields.dueDate;
      order.status = 'registered'; order.statusLabel = 'iCUBE 등록 대기'; order.currentStep = 1;
      order.audit.unshift({at:'방금',actor:order.owner,text:'PO 원본·추출값 검토 완료'});
      break;
    }
    case 'PRODUCTION_APPROVED': {
      const order = state.orders[action.orderId];
      if (order.status === 'complete' || order.deliveredQuantity === order.quantity) throw new Error('완료 수량은 정정업무로 처리하세요.');
      order.productionQuantity = approveProduction({enteredQuantity:action.quantity}).quantity;
      if (action.date) order.productionDueDate = action.date;
      order.audit.unshift({ at: '방금', actor: '김영업', text: `생산요청 ${Number(action.quantity).toLocaleString('ko-KR')} EA를 승인했습니다.` });
      break;
    }
    case 'DOMESTIC_FOLLOWUP_COMPLETED': {
      const order = state.orders[action.orderId];
      if (order.deliveredQuantity !== order.quantity) throw new Error('납품수량이 모두 확정되어야 합니다.');
      if (!action.erpNumber?.trim()) throw new Error('ERP 등록번호를 입력하세요.');
      Object.assign(order,{erpNumber:action.erpNumber,purchaseMailReviewed:true,documentConfirmed:true,status:'complete',statusLabel:'완료',currentStep:4});
      order.audit.unshift({at:'방금',actor:order.owner,text:'ERP 실적·납품서·구매팀 메일 확인 완료'});
      break;
    }
    case 'DELIVERY_ROUND_ADDED': {
      const order=state.orders[action.orderId];const pending=order.deliveries.find(row=>row.actual===null);const quantity=Number(action.quantity);
      if(!pending || !Number.isFinite(quantity) || quantity<=0 || quantity>=pending.planned) throw new Error('분할수량은 현재 예정수량보다 작은 양수여야 합니다.');
      pending.planned-=quantity;
      order.deliveries.push({round:order.deliveries.length+1,date:action.date,planned:quantity,actual:null,status:'예정'});
      break;
    }
    case 'DELIVERY_SCHEDULE_CHANGED': {
      const order=state.orders[action.orderId];const pending=order.deliveries.find(row=>row.actual===null);
      if(!pending) throw new Error('변경할 예정 회차가 없습니다.');
      if(!action.reason?.trim()) throw new Error('일정 변경 사유가 필요합니다.');
      pending.date=action.date;order.audit.unshift({at:'방금',actor:order.owner,text:`납품일 변경 ${action.date}: ${action.reason}`});
      break;
    }
    case 'REVISION_APPROVED': {
      const order = state.orders[action.orderId];
      const quantity = Number(action.quantity);
      if (order.status === 'complete') throw new Error('완료 주문은 정정업무를 생성하세요.');
      if (!Number.isFinite(quantity) || quantity < order.deliveredQuantity) throw new Error('이미 납품된 수량보다 줄일 수 없습니다.');
      order.revisionBefore = order.quantity; order.quantity = quantity;
      const pending=order.deliveries.find(row=>row.actual===null);
      if(pending) pending.planned=quantity-order.deliveredQuantity;
      order.audit.unshift({at:'방금',actor:order.owner,text:`수정본 승인: PO 수량 ${quantity} EA (이미 납품 ${order.deliveredQuantity} EA 보존)`});
      break;
    }
    case 'QY_LINK_CONFIRMED': {
      const order = state.orders[action.orderId];
      if (!action.qy?.length || !action.qp?.length) throw new Error('QY와 QP를 각각 선택하세요.');
      if (canAdvanceOverseas(order).next !== 'confirm-qy-link') throw new Error('업무 순서와 차이 사유를 먼저 확인하세요.');
      order.links={qy:[...action.qy],qp:[...action.qp]}; order.qyLinkConfirmed=true; order.currentStep=4;
      break;
    }
    case 'OVERSEAS_STEP_COMPLETED': {
      const order = state.orders[action.orderId];
      if (canAdvanceOverseas(order).next !== action.step) throw new Error('업무 순서에 맞는 다음 단계를 진행하세요.');
      if (action.step === 'confirm-discrepancy' && !action.reason?.trim()) throw new Error('차이 확인 사유를 입력하세요.');
      const updates = {
        'send-qy': { qySent: true, stage: 'qy-sent' },
        'confirm-factory-reply': { factoryReplyConfirmed: true, stage: 'factory-confirmed' },
        'record-qp': { stage: 'qp-recorded' },
        'confirm-discrepancy': { discrepancyConfirmed: true },
        'confirm-qy-link': { qyLinkConfirmed: true, currentStep: 4, statusLabel: '고객메일 대기' },
        'customer-mail': { customerMailSent: true },
        'import-register': { importRegistered: true },
        receipt: { receiptRecorded: true },
        'internal-mail': { internalMailSent: true, currentStep: 5, status: 'complete', statusLabel: '완료' }
      };
      Object.assign(order, updates[action.step] || {});
      if (action.erpNumber) order.erpNumber=action.erpNumber;
      if (action.step === 'receipt') {order.actualDate=action.date || '2026-10-22';order.deliveredQuantity=order.actualQuantity;}
      if (action.step === 'internal-mail') {
        order.remainingQuantity=Math.max(0,order.quantity-order.actualQuantity);
        if (order.remainingQuantity) {order.status='partial';order.statusLabel=`부분선적 완료 · 잔량 ${order.remainingQuantity} EA`;order.currentStep=4;}
      }
      if (action.reason && action.step === 'confirm-discrepancy') order.discrepancyReason = action.reason.trim();
      else if (action.reason) order.manualErpReason = action.reason.trim();
      order.audit.unshift({ at: '방금', actor: '김영업', text: `${action.label || action.step} 단계를 완료했습니다.` });
      break;
    }
    case 'QP_RECORDED': {
      const order = state.orders[action.orderId];
      if (!order.qySent || !order.factoryReplyConfirmed || order.qyLinkConfirmed) throw new Error('공장 회신 확인 후 연결 확정 전에 입력하세요.');
      const values = action.values;
      if (!values.qpNumber?.trim() || !values.onBoard || !values.etd || !Number.isFinite(Number(values.actualQuantity)) || Number(values.actualQuantity) <= 0) throw new Error('QP·ON BOARD·ETD·실제수량을 입력하세요.');
      if (values.etaStatus === '확정' && !values.eta) throw new Error('확정 ETA 날짜를 입력하세요.');
      const discrepancy = Number(values.actualQuantity) !== order.quantity || values.onBoard !== values.etd || Boolean(values.eta && values.etd > values.eta);
      Object.assign(order, values, {actualQuantity:Number(values.actualQuantity),stage:'qp-recorded',discrepancy,discrepancyConfirmed:false});
      order.audit.unshift({at:'방금',actor:order.owner,text:'QP·선적정보 수동입력 저장'});
      break;
    }
    case 'QY_DRAFT_CHANGED': {
      const order=state.orders[action.orderId];
      if(order.qySent) throw new Error('발송한 QY는 변경할 수 없습니다.');
      if(!['VSL','AIR'].includes(action.mode)) throw new Error('운송방식을 선택하세요.');
      order.qyNumber=formatQyNumber({...order,exw:action.exw,mode:action.mode});order.exw=action.exw;order.mode=action.mode;
      break;
    }
    case 'SCENARIO_CHANGED': {
      const order = state.orders[action.orderId];
      Object.assign(order,{qySent:false,factoryReplyConfirmed:false,qyLinkConfirmed:false,customerMailSent:false,importRegistered:false,receiptRecorded:false,internalMailSent:false,discrepancy:false,discrepancyConfirmed:false,qpNumber:'',onBoard:'',etd:'',eta:'',actualQuantity:null,status:'shipment-ready',stage:action.scenario,currentStep:1});
      if (action.scenario !== 'qy-draft') { order.qySent = true; order.currentStep = 2; }
      if (['factory-confirmed','discrepancy'].includes(action.scenario)) { order.factoryReplyConfirmed = true; order.currentStep = 3; }
      if (action.scenario === 'discrepancy') Object.assign(order,{stage:'qp-recorded',qpNumber:'QP-DEMO-01',onBoard:'2026-10-16',etd:'2026-10-17',eta:'2026-10-22',actualQuantity:3900,discrepancy:true});
      order.statusLabel = { 'qy-draft':'QY 초안','qy-sent':'공장 회신 대기','factory-confirmed':'QP 입력 대기',discrepancy:'선적 차이 확인' }[action.scenario];
      break;
    }
    case 'CORRECTION_CREATED': {
      const order = state.orders[action.orderId];
      if (order.status !== 'complete') throw new Error('완료된 업무에서 정정업무를 생성하세요.');
      if (!Number.isFinite(Number(action.quantity)) || Number(action.quantity) <= 0) throw new Error('정정 수량을 입력하세요.');
      const key = order.type === 'overseas' ? 'actualQuantity' : 'deliveredQuantity';
      const result = createCorrection(order,{[key]:Number(action.quantity)},action.reason);
      state.corrections.unshift({...result.correction,orderId:order.id});
      break;
    }
    case 'EXCEPTION_RESOLVED': {
      if (!action.reason?.trim()) throw new Error('조치 사유를 입력하세요.');
      const item = state.exceptions.find(item => item.id === action.id);
      if (item.owner !== '김영업') throw new Error('담당자만 조치할 수 있습니다.');
      item.status = '조치 완료'; item.reason = action.reason;
      state.priorityItems = state.priorityItems.filter(item => item.id !== action.id);
      break;
    }
    case 'TOAST_SHOWN': state.toast = action.message; break;
    case 'TOAST_CLEARED': state.toast = null; break;
    default: break;
  }
  emit();
  return state;
}

import { escapeHtml, formatDate, formatQuantity } from '../formatters.js';
import { statusBadge } from '../components.js';

export function formatQyNumber({ exw, sequence, customerCode, mode = 'VSL' }) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(exw || '')) throw new Error('EXW 날짜가 필요합니다.');
  const compact = exw.slice(2).replaceAll('-', '');
  return `QY${compact}-${Number(sequence)}${String(customerCode).toUpperCase()}(${mode})`;
}

export function suggestQyLinks(qp, qyInvoices = []) {
  return qyInvoices.filter(qy => Number(qy.quantity) === Number(qp.actualQuantity) && qy.exw === qp.exw);
}

export function canAdvanceOverseas(order) {
  if (order.discrepancy && !order.discrepancyConfirmed) return { next: 'confirm-discrepancy', blocked: true };
  if (order.stage === 'qy-draft' || order.qySent === false) return { next: 'send-qy', blocked: false };
  if (order.stage === 'qy-sent' || (order.qySent && !order.factoryReplyConfirmed)) return { next: 'confirm-factory-reply', blocked: false };
  if (order.stage === 'factory-confirmed' || (order.factoryReplyConfirmed && !order.qpNumber)) return { next: 'record-qp', blocked: false };
  if (!order.qyLinkConfirmed) return { next: 'confirm-qy-link', blocked: false };
  if (!order.customerMailSent) return { next: 'customer-mail', blocked: false };
  if (!order.importRegistered) return { next: 'import-register', blocked: false };
  if (!order.receiptRecorded) return { next: 'receipt', blocked: false };
  if (!order.internalMailSent) return { next: 'internal-mail', blocked: false };
  return { next: 'complete', blocked: false };
}

export function renderOverseas(order) {
  const next = canAdvanceOverseas(order);
  const actionLabels = {
    'send-qy': 'QY 발송 완료로 표시', 'confirm-factory-reply': '중국 공장 회신 확인',
    'record-qp': 'QP·선적정보 저장', 'confirm-discrepancy': '차이 사유 확인',
    'confirm-qy-link': 'QY 연결 확정', 'customer-mail': '고객메일 초안 검토',
    'import-register': '수입선적등록 완료', receipt: '입고처리 완료',
    'internal-mail': '내부메일 초안 검토', complete: '모든 후속 업무 완료'
  };
  const steps = [
    ['QY 생성·발송', order.qySent, order.qyNumber || formatQyNumber(order), '인보이스 선적서류를 중국 공장에 먼저 전달'],
    ['중국 공장 회신', order.factoryReplyConfirmed, order.factoryReplyConfirmed ? '선적 가능 확인' : '회신 대기', '메일 수신 여부는 담당자가 직접 확인'],
    ['QP·선적정보 입력', Boolean(order.qpNumber), order.qpNumber || '미입력', 'QP, ON BOARD, ETD, ETA, 실제수량을 수동 입력'],
    ['QY 연결 확정', order.qyLinkConfirmed, order.qyLinkConfirmed ? '연결 완료' : '확인 필요', '번호 접미사가 아닌 선적정보로 연결 후보 제안'],
    ['고객메일', order.customerMailSent, order.customerMailSent ? '발신 완료' : '미진행', '첨부와 수신자를 검토한 뒤 초안 확정'],
    ['수입선적등록', order.importRegistered, order.importRegistered ? '등록 완료' : '미진행', 'iCUBE 등록 결과를 수동 기록'],
    ['입고처리', order.receiptRecorded, order.receiptRecorded ? '입고 완료' : '미진행', '실제 입고 완료일 기록'],
    ['내부메일', order.internalMailSent, order.internalMailSent ? '발신 완료' : '미진행', 'Sales Admin 전달 후 업무 완료']
  ];
  return `<div class="scenario-bar"><label>업무 단계 체험 <select data-scenario><option value="" selected>현재 데이터 유지</option value="qy-draft">QY 초안부터</option><option value="qy-sent">공장 회신 대기</option><option value="factory-confirmed">QP 수동입력</option><option value="discrepancy">수량 차이 확인</option></select></label><small>단계를 선택하면 이 주문의 샘플 상태가 바뀝니다.</small></div><div class="detail-columns">
    <div class="detail-main">
      <section class="card flow-card"><div class="card__header"><div><p class="section-kicker">OVERSEAS FLOW</p><h2>해외 주문 업무 순서</h2></div>${statusBadge('순서 고정', 'info')}</div>
        <ol class="vertical-flow">${steps.map(([label, done, value, note], index) => `<li class="${done ? 'is-done' : index === steps.findIndex(step => !step[1]) ? 'is-current' : ''}"><span class="flow-index">${done ? '✓' : index + 1}</span><div><strong>${label}</strong><p>${note}</p></div><em>${escapeHtml(value)}</em></li>`).join('')}</ol>
      </section>
      <section class="card"><div class="card__header"><div><p class="section-kicker">QY INVOICE</p><h2>QY 생성 정보</h2></div>${statusBadge(order.qySent ? '발송 완료' : '초안', order.qySent ? 'success' : 'neutral')}</div>
        <form id="qy-form"><fieldset ${order.qySent ? 'disabled' : ''}><div class="form-grid">${field('EXW', order.exw, 'date','','exw')}<label class="field"><span>운송방식</span><select name="mode"><option ${order.mode==='VSL'?'selected':''}>VSL</option><option ${order.mode==='AIR'?'selected':''}>AIR</option></select></label>${field('고객코드', order.customerCode)}${field('전역 순번', order.sequence, 'number')}<div class="field field--wide"><span>QY 번호 미리보기</span><strong class="document-number">${order.qyNumber}</strong><small>번호 규칙: QY + EXW(yyMMdd) + 전역순번 + 고객코드 + (VSL/AIR)</small></div></div></fieldset></form>
      </section>
      <section class="card"><div class="card__header"><div><p class="section-kicker">FACTORY RESPONSE & QP</p><h2>공장 회신 및 선적정보</h2></div>${statusBadge(order.factoryReplyConfirmed ? '회신 확인' : '회신 대기', order.factoryReplyConfirmed ? 'success' : 'warning')}</div>
        <div class="manual-note"><span aria-hidden="true">i</span><p><strong>수신함 자동조회 없음</strong> · Outlook에서 BL 포함 회신을 확인한 뒤 아래 값을 직접 입력합니다.</p></div>
        <form id="qp-form"><fieldset ${!order.factoryReplyConfirmed || order.qyLinkConfirmed ? 'disabled' : ''}><div class="form-grid">${field('QP 번호', order.qpNumber || '', 'text', '예: QP…','qpNumber')}${field('ON BOARD', order.onBoard || '', 'date','','onBoard')}${field('ETD', order.etd || '', 'date','','etd')}${field('ETA', order.eta || '', 'date','','eta')}${field('실제 선적수량', order.actualQuantity || '', 'number','','actualQuantity')}<label class="field"><span>ETA 상태</span><select name="etaStatus"><option ${order.eta ? 'selected' : ''}>확정</option><option ${!order.eta ? 'selected' : ''}>미정</option><option ${order.etaStatus==='예정'?'selected':' '}>예정</option><option ${order.etaStatus==='전후'?'selected':' '}>전후</option></select></label></div><div class="form-footer"><button type="button" class="button button--secondary" data-action="save-qp">QP·선적정보 저장</button></div></fieldset></form>
        ${order.discrepancy && !order.discrepancyConfirmed ? '<div class="discrepancy-note" role="status">수량 또는 날짜 차이를 확인하세요. 사유 확인 전 후속 업무가 잠깁니다.</div>' : ''}
        <div class="link-suggestion"><div><p class="section-kicker">LINK SUGGESTION</p><strong>연결 후보 ${order.qpNumber ? 1 : 0}건</strong><span>${order.qyNumber}</span></div><div><span>${order.actualQuantity === order.quantity ? '수량 일치' : '수량 확인 필요'}</span><button class="button button--secondary" data-action="advance-overseas" data-next="confirm-qy-link" ${next.next !== 'confirm-qy-link' ? 'disabled' : ''}>이 QY로 확정</button></div></div>
      </section>
      <section class="card"><div class="card__body"><button class="button button--secondary" data-action="manual-link" ${next.next!=='confirm-qy-link'?'disabled':''}>QY / QP 다대다 직접선택</button>${order.links ? `<p class="muted">연결 QY ${order.links.qy.length}건 / QP ${order.links.qp.length}건</p>`:''}${order.remainingQuantity ? `<p class="discrepancy-note">선적 후 잔량 ${formatQuantity(order.remainingQuantity)} EA · 추가 선적 관리 필요</p>`:''}</div></section>
      <section class="card shipment-facts"><div class="card__header"><h2>선적 요약</h2></div><div class="info-grid">${info('QY', order.qyNumber)}${info('QP', order.qpNumber)}${info('실제 수량', `${formatQuantity(order.actualQuantity)} EA`)}${info('ON BOARD', formatDate(order.onBoard))}${info('ETD', formatDate(order.etd))}${info('ETA', formatDate(order.eta))}</div></section>
      <section class="card"><div class="card__header"><h2>최근 이력</h2></div><ol class="timeline">${order.audit.map(item=>`<li><span></span><div><strong>${escapeHtml(item.text)}</strong><small>${escapeHtml(item.at)} · ${escapeHtml(item.actor)}</small></div></li>`).join('')}</ol>${order.discrepancyReason ? `<p class="card__body muted">차이 확인 사유: ${escapeHtml(order.discrepancyReason)}</p>` : ''}</section>
    </div>
    <aside class="action-rail"><div class="action-rail__sticky"><p class="section-kicker">NEXT ACTION</p><h2>${actionLabels[next.next]}</h2><p>${next.blocked ? '차이를 확인하고 사유를 남기기 전에는 고객메일과 ERP 후속 업무가 잠깁니다.' : '현재 단계가 완료되면 다음 업무가 순서대로 열립니다.'}</p><div class="rail-checks"><span>${order.qySent ? '✓' : '○'} QY 공장 발송</span><span>${order.factoryReplyConfirmed ? '✓' : '○'} 선적 가능 회신</span><span>${order.qpNumber ? '✓' : '○'} QP·BL 정보 확인</span><span class="${order.qyLinkConfirmed ? '' : 'is-pending'}">${order.qyLinkConfirmed ? '✓' : '○'} QY 연결 확정</span></div><button class="button button--primary button--block" data-action="advance-overseas" data-next="${next.next}" ${next.next === 'complete' ? 'disabled' : ''}>${actionLabels[next.next]}</button><button class="button button--ghost button--block" data-action="mock-document">QY 문서 미리보기</button><small>모든 버튼은 화면 흐름 확인용이며 외부 메일·ERP에 반영되지 않습니다.</small></div></aside>
  </div>`;
}

const field = (label, value, type = 'text', placeholder = '', name = '') => `<label class="field"><span>${label}</span><input name="${name}" type="${type}" value="${escapeHtml(value ?? '')}" placeholder="${placeholder}" ${!name ? 'readonly' : ''}></label>`;
const info = (label, value) => `<dl class="info-pair"><dt>${label}</dt><dd>${escapeHtml(value || '미정')}</dd></dl>`;

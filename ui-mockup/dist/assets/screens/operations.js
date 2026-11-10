import { escapeHtml, formatQuantity } from '../formatters.js';
import { statusBadge } from '../components.js';

export function canCompleteOrder(order) {
  return Boolean(order.customerMailSent && order.importRegistered && order.receiptRecorded && order.internalMailSent && !order.remainingQuantity);
}

export function selectExcelRows(state) {
  return Object.values(state.orders).flatMap(order => {
    const quantity=order.type==='overseas' ? (order.receiptRecorded ? order.actualQuantity : 0) : order.deliveredQuantity;
    if (!quantity) return [];
    const date=order.type==='overseas' ? order.actualDate || '' : [...(order.deliveries||[])].reverse().find(row=>row.actual)?.actualDate || [...(order.deliveries||[])].reverse().find(row=>row.actual)?.date || '';
    return [{owner:order.owner,customer:order.customer,model:order.model,currency:order.type==='overseas'?'USD':'KRW',price:order.unitPrice || (order.type==='overseas'?8.2:12800),date,quantity}];
  });
}

export function createCorrection(order, change, reason) {
  if (!reason?.trim()) throw new Error('정정 사유가 필요합니다.');
  const original = structuredClone(order);
  return {
    original,
    correction: {
      id: `COR-${order.id}-${Date.now()}`,
      before: Object.fromEntries(Object.keys(change).map(key => [key, original[key]])),
      after: structuredClone(change),
      reason: reason.trim(),
      createdAt: new Date().toISOString()
    }
  };
}

const sections = {
  documents: { eyebrow: 'DOCUMENT CENTER', title: '문서', description: '업무별 생성 문서와 버전을 확인합니다.' },
  mail: { eyebrow: 'OUTBOUND MAIL', title: '발신 메일', description: 'Outlook 초안을 검토하고 발신 완료를 기록합니다.' },
  exceptions: { eyebrow: 'EXCEPTIONS & CORRECTIONS', title: '예외·정정', description: '담당자 판단이 필요한 업무와 정정 이력을 관리합니다.' },
  excel: { eyebrow: 'EXCEL COPY VIEW', title: 'Excel 복사', description: '공유 양식에 붙여넣을 최종 실적만 정리합니다.' }
};

export function renderOperations(route, state) {
  const section = sections[route.section] ? route.section : 'documents';
  const meta = sections[section];
  return `<section class="page-header"><div><p class="eyebrow">${meta.eyebrow}</p><h1>${meta.title}</h1><p class="lede">${meta.description}</p></div>${section === 'excel' ? '<button class="button button--primary" data-action="copy-all">전체 행 복사</button>' : ''}</section>
    <nav class="subnav" aria-label="운영 화면">${Object.entries(sections).map(([key, item]) => `<a href="#/operations/${key}" class="${section === key ? 'is-active' : ''}" ${section === key ? 'aria-current="page"' : ''}>${item.title}</a>`).join('')}</nav>
    ${section === 'documents' ? documentsView(state) : section === 'mail' ? mailView() : section === 'exceptions' ? exceptionView(state) + correctionView(state) : excelView(state)}`;
}

function correctionView(state) {
  return `<section class="card correction-records"><div class="card__header"><h2>정정업무 이력</h2><span class="count">${state.corrections.length}</span></div><div class="card__body">${state.corrections.length ? state.corrections.map(item=>`<p><strong>${item.orderId}</strong> · ${Object.values(item.before)[0]} → ${Object.values(item.after)[0]} EA<br><small class="muted">사유: ${escapeHtml(item.reason)}</small></p>`).join('') : '<p class="muted">아직 생성된 정정업무가 없습니다. 완료 주문에서 생성할 수 있습니다.</p>'}</div></section>`;
}

function documentsView(state) {
  const docs = [
    ['DOC-1017', 'QY Invoice', 'QY261013-40CHVN(VSL).xlsx', 'CV-8821', 'v2', '발송본'],
    ['DOC-1016', '납품서', '범진전자_2차납품서.pdf', 'BJ-10241', 'v1', '검토 중'],
    ['DOC-1015', 'PO 원본', state.poReview.fileName, 'SE-2408', '원본', '검토 필요']
  ];
  return `<section class="card"><div class="card__header"><h2>최근 문서</h2><span class="count">${docs.length}</span></div><div class="table-wrap"><table><thead><tr><th>문서번호</th><th>종류</th><th>파일명</th><th>업무번호</th><th>버전</th><th>상태</th><th></th></tr></thead><tbody>${docs.map(doc => `<tr><td><strong>${doc[0]}</strong></td><td>${doc[1]}</td><td>${doc[2]}</td><td><a class="id-link" href="#/orders/${doc[3]}">${doc[3]}</a></td><td>${doc[4]}</td><td>${statusBadge(doc[5], doc[5] === '발송본' ? 'success' : 'warning')}</td><td><button class="row-open" data-action="mock-document" aria-label="${doc[2]} 보기">›</button></td></tr>`).join('')}</tbody></table></div></section>`;
}

function mailView() {
  return `<div class="mail-layout"><section class="card"><div class="card__header"><h2>발신 대기</h2>${statusBadge('2건 검토 필요', 'warning')}</div><div class="mail-list"><button class="mail-item is-selected"><span class="mail-icon">✉</span><span><strong>[선적안내] CHEMTRO VINA / QP1026…</strong><small>고객메일 · CV-8821 · 방금</small></span><em>초안</em></button><button class="mail-item"><span class="mail-icon">✉</span><span><strong>[납품안내] 범진전자 / 2차 납품</strong><small>구매팀 · BJ-10241 · 12분 전</small></span><em>초안</em></button></div></section>
    <section class="card mail-preview"><div class="card__header"><div><p class="section-kicker">OUTLOOK DRAFT</p><h2>Outlook 초안 검토</h2></div><button class="button button--ghost" data-action="mock-mail">Outlook에서 열기</button></div><div class="mail-fields"><dl><dt>받는 사람</dt><dd>CHEMTRO VINA Shipping Team</dd></dl><dl><dt>참조</dt><dd>Sales Admin · 김영업</dd></dl><dl><dt>제목</dt><dd>[Shipment Notice] CH-88V / QP1026-CHVN35</dd></dl></div><div class="mail-body"><p>Dear CHEMTRO VINA Team,</p><p>Please find the confirmed shipment details for CH-88V.</p><div class="mail-facts"><span>Actual Qty <strong>4,000 EA</strong></span><span>ETD <strong>2026-10-17</strong></span><span>ETA <strong>2026-10-22</strong></span></div><p>Best regards,<br>FLOW Components</p></div><div class="attachment"><span>◇</span><div><strong>QY261013-40CHVN(VSL).xlsx</strong><small>고객용 첨부 · 248 KB</small></div>${statusBadge('첨부 확인', 'success')}</div><div class="mail-actions"><p>실제 발송 전 Outlook에서 수신자와 첨부를 다시 확인합니다.</p><button class="button button--primary" data-action="mock-mail">초안 검토 완료</button></div></section></div>`;
}

function exceptionView(state) {
  return `<div class="exception-grid"><section class="card"><div class="card__header"><h2>조치 필요</h2><span class="count">${state.exceptions.length}</span></div>${state.exceptions.map(item => `<article class="exception-item"><div class="exception-icon">!</div><div><div class="exception-meta">${statusBadge(item.status, 'danger')} <span>${item.id}</span></div><h3>${item.type}</h3><p>PO 단가와 QP 기준 단가가 다릅니다. 담당자가 원본을 확인하고 판단 사유를 남겨야 합니다.</p><a href="#/orders/${item.orderId}">${item.orderId} · CHEMTRO VINA →</a></div><button class="button button--secondary" data-action="resolve-exception">조치하기</button></article>`).join('')}</section><section class="card correction-guide"><div class="card__header"><h2>정정 원칙</h2></div><div class="card__body"><div class="lock-visual">⌑</div><h3>완료값은 직접 덮어쓰지 않습니다.</h3><p>완료된 업무의 원본은 그대로 보존하고, 변경 전·변경 후·사유가 포함된 정정업무를 새로 생성합니다.</p><button class="button button--ghost" data-action="open-correction">정정업무 예시 보기</button></div></section></div>`;
}

function excelView(state) {
  const rows = selectExcelRows(state).map(row=>[row.owner,row.customer,row.model,row.currency,row.price,row.date,row.quantity]);
  return `<section class="card excel-card"><div class="excel-note"><span aria-hidden="true">i</span><p><strong>완료 조건과 무관한 보조 기능입니다.</strong> 아래 값만 복사되며 공유 Excel을 직접 읽거나 쓰지 않습니다.</p></div><div class="table-wrap"><table><thead><tr><th>영업담당</th><th>고객사</th><th>모델</th><th>통화</th><th>단가</th><th>실제일</th><th>최종수량</th><th></th></tr></thead><tbody>${rows.map((row, index) => `<tr>${row.map((cell, i) => `<td>${i === 6 ? `${formatQuantity(cell)} EA` : cell}</td>`).join('')}<td><button class="button button--ghost button--small" data-action="copy-row" data-row="${index}">행 복사</button></td></tr>`).join('')}</tbody></table></div><footer class="excel-footer"><span>열 순서: 담당자 → 고객사 → 모델 → 통화 → 단가 → 실제일 → 최종수량</span><span>${rows.length}행 준비됨</span></footer></section>`;
}

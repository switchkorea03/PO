import { escapeHtml, formatDate, formatQuantity } from '../formatters.js';
import { statusBadge } from '../components.js';

export function confirmDelivery(order, quantity) {
  const next = Number(order.deliveredQuantity || 0) + Number(quantity || 0);
  if (!Number.isFinite(Number(quantity)) || !Number.isFinite(next) || Number(quantity) <= 0) throw new Error('실제 납품수량을 입력하세요.');
  if (next > order.quantity) throw new Error('납품 합계가 PO 수량을 초과합니다.');
  return { deliveredQuantity: next, remainingQuantity: order.quantity - next };
}

export function approveProduction({ enteredQuantity }) {
  const quantity = Number(enteredQuantity);
  if (!Number.isFinite(quantity) || quantity <= 0) throw new Error('생산요청 수량을 입력하세요.');
  return { quantity, approved: true };
}

export function renderDomestic(order) {
  const remaining = Math.max(0, order.quantity - order.deliveredQuantity);
  const firstPending = order.deliveries.find(row=>row.actual===null);
  return `<div class="detail-columns">
    <div class="detail-main">
      <section class="card info-card"><div class="card__header"><div><p class="section-kicker">ORDER SUMMARY</p><h2>주문 정보</h2></div><a class="text-link" href="#/review/SE-2408">PO 원본 보기</a></div>
        <div class="info-grid">${info('PO 번호', order.poNumber)}${info('모델', order.model)}${info('PO 수량', `${formatQuantity(order.quantity)} EA`)}${info('요청 납기', formatDate(order.dueDate))}${info('담당자', order.owner)}${info('고객사', order.customer)}</div></section>
      <section class="card"><div class="card__header"><div><p class="section-kicker">PRODUCTION</p><h2>재고 참고 및 생산요청</h2></div>${statusBadge('담당자 단독 승인', 'neutral')}</div>
        <div class="production-grid"><div class="stock-tile"><span>현재 참고재고</span><strong>${formatQuantity(order.stock)} <small>EA</small></strong><p>재고는 참고값이며 요청수량을 자동 계산하지 않습니다.</p></div><form class="inline-form" data-form="production"><label>생산요청 수량<input id="production-qty" type="number" min="1" value="${order.productionQuantity || ''}" placeholder="직접 입력" ${!remaining?'disabled':''} aria-describedby="production-help"></label><label>생산 요청일<input id="production-date" type="date" value="${order.productionDueDate}" ${!remaining?'disabled':''}></label><small id="production-help">수량은 담당자가 직접 판단해 입력합니다.</small><button type="button" class="button button--secondary" data-action="approve-production" ${!remaining?'disabled':''}>생산요청 승인</button></form></div>
      </section>
      <section class="card delivery-card"><div class="card__header"><div><p class="section-kicker">DELIVERY ROUNDS</p><h2>분할납품</h2></div><div class="quantity-summary"><span>납품 ${formatQuantity(order.deliveredQuantity)}</span><strong>잔량 ${formatQuantity(remaining)} EA</strong></div></div>
        <div class="table-wrap"><table><thead><tr><th>회차</th><th>예정일</th><th>예정수량</th><th>실제 납품수량</th><th>상태</th></tr></thead><tbody>${order.deliveries.map(row => `<tr><td>${row.round}차</td><td>${row.date}</td><td>${formatQuantity(row.planned)} EA</td><td>${row.actual ? `${formatQuantity(row.actual)} EA` : row===firstPending ? `<label class="cell-input"><span class="sr-only">${row.round}차 실제 납품수량</span><input id="delivery-qty" type="number" min="1" max="${remaining}" value="${row.planned}"></label>` : '다음 회차'}</td><td>${statusBadge(row.status, row.status === '완료' ? 'success' : 'neutral')}</td></tr>`).join('')}</tbody></table></div>
        <div class="delivery-actions"><p><span aria-hidden="true">i</span> 실제수량 합계는 PO 수량 ${formatQuantity(order.quantity)} EA를 넘을 수 없습니다.</p><button class="button button--primary" data-action="confirm-delivery" ${remaining === 0 ? 'disabled' : ''}>실제수량 확정</button></div>
      </section>
      <section class="card"><div class="card__header"><h2>납품 후속처리</h2>${statusBadge(order.status==='complete'?'완료':'실적 확정 후 진행',order.status==='complete'?'success':'neutral')}</div><div class="card__body"><label class="field"><span>실제 납품일</span><input id="actual-delivery-date" type="date" value="2026-10-13" ${order.status==='complete'?'disabled':''}></label><button class="button button--secondary button--block" data-action="domestic-followup" ${remaining || order.status==='complete' ? 'disabled' : ''}>ERP 실적·납품서·구매팀 메일 확인</button></div></section>
      ${remaining ? '<div class="header-actions"><button class="button button--secondary" data-action="add-delivery">분할 회차 추가</button><button class="button button--ghost" data-action="edit-delivery">예정일 변경·사유 기록</button></div>' : ''}
      ${renderTimeline(order.audit)}
    </div>
    <aside class="action-rail"><div class="action-rail__sticky"><p class="section-kicker">NEXT ACTION</p><h2>${remaining ? '실제 납품 확정' : '납품 완료'}</h2><p>납품서와 실제 납품수량을 확인한 뒤 확정하세요.</p><div class="rail-checks"><span>✓ 납품 예정일 확인</span><span class="${remaining ? 'is-pending' : ''}">${remaining ? '○ 실제 수량 확인 필요' : '✓ 전체 납품 완료'}</span></div><button class="button button--primary button--block" data-action="confirm-delivery" ${remaining === 0 ? 'disabled' : ''}>${remaining ? formatQuantity(remaining)+' EA 확정' : '전체 수량 확정 완료'}</button><button class="button button--ghost button--block" data-action="mock-document">납품서 미리보기</button><small>확정 후 구매팀 발신메일 초안을 검토합니다.</small></div></aside>
  </div>`;
}

const info = (label, value) => `<dl class="info-pair"><dt>${label}</dt><dd>${escapeHtml(value)}</dd></dl>`;
const renderTimeline = audit => `<section class="card timeline-card"><div class="card__header"><h2>최근 이력</h2></div><ol class="timeline">${audit.map(item => `<li><span></span><div><strong>${escapeHtml(item.text)}</strong><small>${item.at} · ${item.actor}</small></div></li>`).join('')}</ol></section>`;

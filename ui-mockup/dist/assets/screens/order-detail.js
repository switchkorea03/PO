import { renderStepper, statusBadge } from '../components.js';
import { renderDomestic } from './domestic.js';
import { escapeHtml } from '../formatters.js';

export function renderOrderDetail(order, renderOverseas = null) {
  if (!order) return `<section class="empty-state"><h1>주문을 찾을 수 없습니다.</h1><a class="button button--primary" href="#/orders">PO 목록으로</a></section>`;
  const tone = order.type === 'overseas' ? 'info' : 'warning';
  const body = order.type === 'overseas' && renderOverseas ? renderOverseas(order) : renderDomestic(order);
  const poNumber = escapeHtml(order.poNumber), model = escapeHtml(order.model);
  return `<section class="detail-heading"><div><div class="detail-heading__meta"><a href="#/orders">← PO 업무</a>${statusBadge(order.typeLabel, 'neutral')} ${statusBadge(order.statusLabel, tone)}</div><h1>${order.customer} <span>${order.id}</span></h1><p>${poNumber} · ${model}</p></div><div class="header-actions"><button class="button button--ghost" data-action="mock-document">문서 보기</button><button class="button button--secondary" data-action="open-correction">정정업무 생성</button></div></section>
    <section class="stepper-card">${renderStepper(order.milestones, order.currentStep)}</section>${body}`;
}

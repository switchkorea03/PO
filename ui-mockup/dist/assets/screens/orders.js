import { escapeHtml, formatDate, formatQuantity } from '../formatters.js';
import { filterOrders } from '../store.js';
import { statusBadge } from '../components.js';

export function renderOrders(state, filters = {}) {
  const orders = filterOrders(state.orders, filters);
  return `<section class="page-header"><div><p class="eyebrow">PO WORKLIST</p><h1>PO 업무</h1><p class="lede">검토부터 납품·선적 완료까지 한 목록에서 관리합니다.</p></div><a class="button button--primary" href="#/review/SE-2408">신규 PO 검토</a></section>
    <section class="card filter-card" aria-label="PO 검색 및 필터">
      <div class="filter-bar">
        <label class="search-field"><span class="sr-only">PO 검색</span><span aria-hidden="true">⌕</span><input data-filter="search" type="search" value="${escapeHtml(filters.search || '')}" placeholder="PO 검색 · 고객사, 모델, 번호"></label>
        ${select('owner', '담당자', ['전체', '김영업', '박해외'], filters.owner || '전체')}
        ${select('type', '구분', [['all','전체 구분'],['domestic','국내'],['overseas','해외']], filters.type || 'all')}
        ${select('status', '상태', [['all','전체 상태'],['review','PO 검토 필요'],['delivery','분할납품 진행'],['shipment-ready','QP 연결 확인']], filters.status || 'all')}
        <button class="button button--ghost" data-action="clear-filters">필터 초기화</button>
      </div>
      <div class="result-meta"><strong>${orders.length}건</strong><span>최근 업데이트 순</span></div>
      <div class="table-wrap"><table><thead><tr><th>업무번호</th><th>고객사</th><th>모델</th><th>구분</th><th>PO 수량</th><th>납기</th><th>담당자</th><th>상태</th><th><span class="sr-only">열기</span></th></tr></thead><tbody>
        ${orders.length ? orders.map(order => `<tr><td><a class="id-link" href="#/orders/${order.id}">${order.id}</a><small>${order.poNumber}</small></td><td><strong>${order.customer}</strong></td><td>${order.model}</td><td>${order.typeLabel}</td><td>${formatQuantity(order.quantity)} EA</td><td>${formatDate(order.dueDate)}</td><td>${order.owner}</td><td>${statusBadge(order.statusLabel, order.status === 'review' ? 'warning' : 'info')}</td><td><a class="row-open" href="#/orders/${order.id}" aria-label="${order.id} 상세 열기">›</a></td></tr>`).join('') : `<tr><td colspan="9"><div class="empty-state"><strong>조건에 맞는 PO가 없습니다.</strong><span>필터를 바꾸거나 초기화해 보세요.</span></div></td></tr>`}
      </tbody></table></div>
    </section>`;
}

function select(name, label, options, value) {
  const normalized = options.map(option => Array.isArray(option) ? option : [option, option]);
  return `<label class="select-field"><span class="sr-only">${label}</span><select data-filter="${name}">${normalized.map(([key, text]) => `<option value="${key}" ${key === value ? 'selected' : ''}>${text}</option>`).join('')}</select></label>`;
}

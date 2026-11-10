import { formatDate, formatQuantity } from '../formatters.js';
import { selectPriorityWork } from '../store.js';
import { statusBadge } from '../components.js';

export function renderDashboard(state) {
  const orders = Object.values(state.orders);
  const priorities = selectPriorityWork(state);
  const dueToday = orders.filter(order => order.dueDate === '2026-10-13');
  const dueTomorrow = orders.filter(order => order.dueDate === '2026-10-14');
  return `<section class="page-header">
      <div><p class="eyebrow">TUESDAY · 2026.10.13</p><h1>오늘의 업무</h1><p class="lede">막힌 업무와 오늘 마감 건을 먼저 확인하세요.</p></div>
      <a class="button button--primary" href="#/review/SE-2408"><span aria-hidden="true">＋</span> 신규 PO 검토</a>
    </section>
    <section class="metric-grid" aria-label="업무 현황 요약">
      ${metric('오늘 처리', 4, '2건 긴급', 'warning')}
      ${metric('진행 중 PO', orders.length, '국내 2 · 해외 1', 'info')}
      ${metric('예외·정정', state.exceptions.length, '담당자 조치 필요', 'danger')}
      ${metric('이번 주 완료', 12, '지난주 대비 +3', 'success')}
    </section>
    <div class="dashboard-grid">
      <section class="card priority-card">
        <div class="card__header"><div><p class="section-kicker">ACTION QUEUE</p><h2>우선 처리 업무</h2></div><span class="count">${priorities.length}</span></div>
        <div class="work-list">${priorities.map((item, index) => `<a class="work-item" href="${item.href}">
          <span class="work-rank">0${index + 1}</span><span class="work-copy"><strong>${item.title}</strong><small>${item.subtitle}</small></span>
          ${statusBadge(item.due, item.severity)}<span class="chevron" aria-hidden="true">›</span>
        </a>`).join('')}</div>
      </section>
      <section class="card schedule-card">
        <div class="card__header"><div><p class="section-kicker">SCHEDULE</p><h2>오늘·내일 일정</h2></div><a href="#/orders">전체보기</a></div>
        <div class="day-block"><div class="day-label"><strong>오늘</strong><span>10.13</span></div><div class="day-items">${dueToday.map(scheduleRow).join('') || empty('일정 없음')}</div></div>
        <div class="day-block"><div class="day-label day-label--muted"><strong>내일</strong><span>10.14</span></div><div class="day-items">${dueTomorrow.map(scheduleRow).join('') || empty('일정 없음')}</div></div>
      </section>
    </div>
    <section class="card recent-card">
      <div class="card__header"><div><p class="section-kicker">ACTIVE ORDERS</p><h2>진행 중 PO</h2></div><a class="text-link" href="#/orders">업무 목록 열기 →</a></div>
      <div class="table-wrap"><table><thead><tr><th>업무번호</th><th>고객사 / 모델</th><th>구분</th><th>PO 수량</th><th>납기</th><th>현재 상태</th></tr></thead><tbody>
      ${orders.map(order => `<tr data-href="#/orders/${order.id}" tabindex="0"><td><a href="#/orders/${order.id}"><strong>${order.id}</strong></a><small>${order.poNumber}</small></td><td><strong>${order.customer}</strong><small>${order.model}</small></td><td>${order.typeLabel}</td><td>${formatQuantity(order.quantity)} EA</td><td>${formatDate(order.dueDate)}</td><td>${statusBadge(order.statusLabel, order.status === 'review' ? 'warning' : 'info')}</td></tr>`).join('')}
      </tbody></table></div>
    </section>`;
}

const metric = (label, value, note, tone) => `<article class="metric-card"><div class="metric-card__top"><span>${label}</span><span class="metric-icon metric-icon--${tone}" aria-hidden="true">${tone === 'danger' ? '!' : tone === 'success' ? '✓' : '↗'}</span></div><strong>${value}</strong><small>${note}</small></article>`;
const scheduleRow = order => `<a class="schedule-row" href="#/orders/${order.id}"><span class="schedule-time">${order.type === 'overseas' ? '선적' : '납품'}</span><span><strong>${order.customer}</strong><small>${order.model} · ${formatQuantity(order.quantity)} EA</small></span><span class="chevron">›</span></a>`;
const empty = text => `<p class="empty">${text}</p>`;

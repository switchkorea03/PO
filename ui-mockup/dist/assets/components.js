import { escapeHtml } from './formatters.js';

const navItems = [
  ['/', '오늘의 업무', '⌂'], ['/orders', 'PO 업무', '▤'], ['/operations/documents', '문서', '◇'],
  ['/operations/mail', '발신 메일', '✉'], ['/operations/exceptions', '예외·정정', '!'],
  ['/operations/excel', 'Excel 복사', '▦'], ['/master', '기준정보', '⚙']
];

export function statusBadge(label, tone = 'neutral') {
  return `<span class="badge badge--${tone}"><span aria-hidden="true" class="badge__dot"></span>${escapeHtml(label)}</span>`;
}

export function renderShell(content, context = {}) {
  const active = context.active || '/';
  return `<div class="app-shell">
    <aside class="sidebar" aria-label="주요 메뉴">
      <a class="brand" href="#/"><span class="brand__mark">F</span><span><strong>FlowPO</strong><small>ORDER OPERATIONS</small></span></a>
      <nav>${navItems.map(([href, label, icon]) => `<a href="#${href}" class="nav-link ${active === href ? 'is-active' : ''}" ${active === href ? 'aria-current="page"' : ''}><span aria-hidden="true">${icon}</span><span>${label}</span></a>`).join('')}</nav>
      <div class="sidebar__foot"><span class="safe-indicator"><span>●</span> 데모 안전 모드</span><small>외부 전송·ERP 반영 없음</small></div>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <button class="icon-button mobile-menu" data-action="toggle-nav" aria-label="메뉴 열기">☰</button>
        <div class="breadcrumb">${escapeHtml(context.eyebrow || 'PO 운영')} <span>/</span> <strong>${escapeHtml(context.title || '오늘의 업무')}</strong></div>
        <div class="topbar__actions"><span class="mode-pill"><span>●</span> MOCK DATA</span><button class="button button--ghost" data-action="reset-demo">초기화</button><button class="avatar" aria-label="사용자 메뉴">김</button></div>
      </header>
      <main id="main-content" class="main" tabindex="-1">${content}</main>
    </div>
  </div>`;
}

export function renderStepper(steps = [], current = 0) {
  return `<ol class="stepper" aria-label="업무 진행 단계">${steps.map((step, index) => `<li class="${index < current ? 'is-done' : index === current ? 'is-current' : ''}" ${index === current ? 'aria-current="step"' : ''}><span>${index < current ? '✓' : index + 1}</span><em>${escapeHtml(step)}</em></li>`).join('')}</ol>`;
}

export function showToast(message) {
  const region = document.querySelector('#toast-region');
  if (!region) return;
  region.innerHTML = `<div class="toast"><span aria-hidden="true">✓</span>${escapeHtml(message)}</div>`;
  window.setTimeout(() => { region.innerHTML = ''; }, 2800);
}

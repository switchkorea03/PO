import { escapeHtml } from '../formatters.js';
import { statusBadge } from '../components.js';

export function selectSourceRegion(review, fieldKey) {
  const field = review.fields.find(item => item.key === fieldKey);
  return review.regions.find(region => region.id === field?.regionId) || null;
}

export function renderPoReview(state) {
  const review = state.poReview;
  const selected = state.selectedField || review.fields[0].key;
  return `<section class="page-header"><div><p class="eyebrow">PO REVIEW · P1</p><h1>원본과 추출값 연결 검토</h1><p class="lede">오른쪽 필드를 선택하면 원본의 대응 위치가 강조됩니다.</p></div><div class="header-actions"><a class="button button--ghost" href="#/orders">나중에 검토</a><button class="button button--primary" data-action="confirm-review">확인 후 업무 생성</button></div></section>
    <div class="scenario-bar"><span>예외 상황 체험</span><button class="button button--ghost" data-action="review-duplicate">동일 파일 중복</button><button class="button button--ghost" data-action="review-revision">부분납품 후 수정본</button></div><div class="review-layout">
      <section class="document-panel" aria-label="PO 원본 미리보기">
        <div class="document-toolbar"><span><strong>${escapeHtml(review.fileName)}</strong><small>PDF · 1페이지</small></span><span class="zoom-control">−&nbsp;&nbsp; 85% &nbsp;&nbsp;+</span></div>
        <div class="pdf-stage"><div class="pdf-page">
          <div class="pdf-logo">SERIM<br><small>MOTORS</small></div><div class="pdf-title">PURCHASE ORDER</div>
          <div class="pdf-meta">PO No. <strong>PO-2026-1012-11</strong><br>Date. 2026-10-12</div>
          <div class="pdf-address"><strong>SUPPLIER</strong><br>FLOW COMPONENTS CO., LTD.<br><br><strong>SHIP TO</strong><br>SERIM MOTORS · HWASEONG</div>
          <table class="pdf-table"><thead><tr><th>ITEM</th><th>DESCRIPTION</th><th>QTY</th><th>UNIT PRICE</th></tr></thead><tbody><tr><td>SM-402</td><td>MOTOR CONTROL MODULE</td><td>2,500 EA</td><td>KRW 12,800</td></tr></tbody></table>
          <div class="pdf-total">DELIVERY: 2026-10-14<br><strong>TOTAL KRW 32,000,000</strong></div>
          ${review.regions.map(region => `<button class="pdf-region ${selected && selectSourceRegion(review, selected)?.id === region.id ? 'is-selected' : ''}" style="left:${region.x}%;top:${region.y}%;width:${region.w}%;height:${region.h}%" data-field-region="${region.id}" aria-label="${region.label} 원본 영역"></button>`).join('')}
        </div></div>
      </section>
      <aside class="review-fields" aria-label="추출 필드 검토">
        <div class="review-summary"><div><p class="section-kicker">EXTRACTION CONFIDENCE</p><strong>${review.confidence}%</strong></div>${statusBadge(`${review.fields.filter(field=>field.confidence<80&&!field.confirmed).length}개 확인 필요`, 'warning')}</div>
        <div class="field-list">${review.fields.map(field => `<button class="field-row ${field.key === selected ? 'is-selected' : ''}" data-action="select-field" data-field="${field.key}" aria-pressed="${field.key === selected}"><span><small>${field.label}</small><strong>${escapeHtml(field.value)}</strong></span><span class="confidence confidence--${field.confidence < 80 ? 'low' : 'high'}">${field.confidence}%</span></button>`).join('')}</div>
        <div class="review-note"><strong>검토 기준</strong><p>수량·단가처럼 신뢰도 80% 미만인 값은 원본 위치를 확인한 뒤 승인하세요.</p><p>${review.fields.filter(field=>field.confirmed).map(field=>field.label+' 확인 완료').join(' · ') || '수량·단가 확인 대기'}</p><button class="button button--secondary button--block" data-action="edit-field">선택 필드 수정·확인</button></div>
        <div class="duplicate-alert"><span aria-hidden="true">i</span><div><strong>중복 검사를 완료했습니다.</strong><small>동일 고객사·PO 번호의 기존 업무가 없습니다.</small></div></div>
      </aside>
    </div>`;
}

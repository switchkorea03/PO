import { statusBadge } from '../components.js';

export function renderMasterData() {
  const groups = [
    { title: '고객사', count: 18, description: '국내·해외 구분, 고객코드, 기본 통화', samples: ['범진전자 · BJ', 'CHEMTRO VINA · CHVN'] },
    { title: '품목·단위', count: 126, description: '모델명, 기본단위, 표기명', samples: ['BCM-24A · EA', 'CH-88V · EA'] },
    { title: '문서 템플릿', count: 6, description: 'QY Invoice, 납품서, 출고명세서', samples: ['QY Invoice · v3', '국내 납품서 · v2'] },
    { title: '수신자 그룹', count: 9, description: '고객·공장·내부 발신 대상', samples: ['CHEMTRO Shipping', 'Sales Admin'] }
  ];
  return `<section class="page-header"><div><p class="eyebrow">MASTER DATA</p><h1>기준정보</h1><p class="lede">문서와 발신 초안에 사용하는 업무 기준값을 관리합니다.</p></div><button class="button button--primary" data-action="mock-master-add">기준정보 추가</button></section><div class="master-grid">${groups.map(group => `<section class="card master-card"><div class="card__header"><div><p class="section-kicker">${group.count} RECORDS</p><h2>${group.title}</h2></div>${statusBadge('정상', 'success')}</div><div class="card__body"><p>${group.description}</p><ul>${group.samples.map(sample => `<li><span>${sample}</span><button data-action="mock-master-edit" aria-label="${sample} 편집">편집</button></li>`).join('')}</ul><button class="button button--ghost button--block" data-action="mock-master-edit">${group.title} 전체 관리</button></div></section>`).join('')}</div><section class="safe-panel"><div class="safe-panel__icon">⌁</div><div><strong>민감정보는 이 화면에서 관리하지 않습니다.</strong><p>메일 계정 비밀번호, ERP 인증정보, API 키는 별도의 보안 저장소를 사용해야 합니다.</p></div></section>`;
}

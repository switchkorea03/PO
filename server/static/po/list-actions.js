// Use normal POST navigation so deletion does not depend on JSON/module loading.
for (const form of document.querySelectorAll('[data-delete-po-form]')) {
 form.addEventListener('submit', event => {
  if (!window.confirm(`PO ${form.dataset.poNumber}\n이 PO 전체를 휴지통으로 이동할까요? 원본과 이력은 보존되며 복원할 수 있습니다.`)) {
   event.preventDefault();
   return;
  }
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  button.textContent = '삭제 중…';
 });
}

const form=document.querySelector('#order-form');
const initial=JSON.parse(document.querySelector('#order-data').textContent);
const draftId=location.pathname.split('/')[2];
form.dataset.url=`/intake/${draftId}/confirm/`;
for(const [name,value] of Object.entries({draft_version:initial.draft_version,target_order_id:initial.target_order_id||''})){
 const input=document.createElement('input');input.type='hidden';input.name=name;input.value=value;form.append(input);
}
await import('./orders.js?v=20261103-spec-aliases');
await import('./gemini.js?v=20261103-gemini-final');

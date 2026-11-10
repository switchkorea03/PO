import {postJson,showError,escapeHtml as esc} from './api.js';
import {groupDigits} from './numbers.js';
const orderForm=document.querySelector('#order-form');
if(orderForm){
 const itemMapping=JSON.parse(document.querySelector('#item-mapping-data')?.textContent||'{}');
 const internalNames=JSON.parse(document.querySelector('#internal-names-data')?.textContent||'[]');
 const specAliases=JSON.parse(document.querySelector('#spec-aliases-data')?.textContent||'{}');
 const specModels=[...internalNames.map(model=>[model,model]),...Object.entries(specAliases)].map(([token,model])=>({model,pattern:new RegExp('(^|[^A-Z0-9-])'+token.split('').join('\\s*')+'(?![A-Z0-9-])','i')}));
 let bulkDue='';
 const data=JSON.parse(document.querySelector('#order-data').textContent);const rows=document.querySelector('#line-rows');
 const tableMode=rows.tagName==='TBODY';
 for(const [key,value] of Object.entries(data)){const input=orderForm.elements.namedItem(key);if(input&&key!=='lines')input.value=value??'';}
 if(!data.row_version&&!orderForm.elements.received_on.value)orderForm.elements.received_on.value=orderForm.elements.received_on.dataset.default;
 if(!data.customer_id&&data.customer_name){document.querySelector('#customer-name').value=data.customer_name;document.querySelector('#customer-type').value=data.order_type||'domestic';document.querySelector('#customer-currency').value=data.lines?.[0]?.currency||'KRW';}
 function addLine(line={}){
  if(bulkDue&&!line.requested_due)line={...line,requested_due:bulkDue};
  const row=document.createElement(tableMode?'tr':'fieldset');row.className='line-row';if(line.id)row.dataset.id=line.id;
  const fields=[['code','고객품목명','text'],['name','스펙','text'],['internal_name','자사품목명','text'],['quantity','수량','number'],['unit_price','단가','number'],['source_amount','공급가액','number'],['requested_due','납기일','date'],['unit','단위','text'],['currency','통화','text']];
  const cell=html=>tableMode?`<td>${html}</td>`:html;
  const input=(key,visible=false)=>{const [,label,type]=fields.find(item=>item[0]===key);let value=String(line[key]??({unit:'EA',currency:'KRW'}[key]||''));if(type==='number')value=value.replace(/(\.\d*?[1-9])0+$|\.0+$/,'$1');if(key==='quantity')value=groupDigits(value.replaceAll(',',''));return `<label><span ${tableMode&&!visible?'class="sr-only"':''}>${label}</span><input data-field="${key}" type="${key==='quantity'?'text':type}" ${key==='quantity'?'inputmode="decimal"':type==='number'?'step="any" min="0"':''} value="${esc(value)}"></label>`;};
  const controls=cell(`<output class="item-name-preview ${tableMode?'sr-only':''}" data-item-name aria-live="polite"></output><button type="button" data-remove-line>삭제</button>`);
  row.innerHTML=(tableMode?['internal_name','code','name','quantity','unit','unit_price','currency','source_amount','requested_due'].map(key=>cell(input(key))).join(''):'<legend>PO 품목</legend>'+fields.map(([key])=>input(key,true)).join(''))+controls;
  const field=key=>row.querySelector(`[data-field="${key}"]`);
  const suggested=()=>{const spec=field('name').value.replace(/[‐‑‒–—−]/g,'-');const matches=[...new Set(specModels.filter(item=>item.pattern.test(spec)).map(item=>item.model))];if(matches.length)return matches.length===1?matches[0]:'';return itemMapping[field('code').value.trim().toUpperCase()]||itemMapping[field('name').value.trim().toUpperCase()]||'';};
  let automatic=suggested();if(!field('internal_name').value)field('internal_name').value=automatic;
  const preview=()=>{const name=field('code').value||field('name').value;const own=field('internal_name').value;const qty=groupDigits(field('quantity').value.replaceAll(',',''));row.querySelector('[data-item-name]').textContent=(name?(name+(own?` (${own})`:'')):'고객품목명을 입력하세요.')+(qty?` · ${qty} ${field('unit').value}`:'');};
  field('quantity').addEventListener('blur',event=>event.target.value=groupDigits(event.target.value.replaceAll(',','')));
  row.addEventListener('input',event=>{if(['code','name'].includes(event.target.dataset.field)){const next=suggested();if(!field('internal_name').value||field('internal_name').value===automatic)field('internal_name').value=next;automatic=next;}preview();});
  row.querySelector('[data-remove-line]').onclick=()=>row.remove();rows.append(row);preview();
 }
 (data.lines?.length?data.lines:[{}]).forEach(addLine);document.querySelector('#add-line').onclick=()=>addLine();
 const bulkButton=document.querySelector('#apply-bulk-due');
 if(bulkButton)bulkButton.onclick=()=>{
  const date=document.querySelector('#bulk-due');const status=document.querySelector('#bulk-due-status');
  if(!date.value){status.textContent='전체 적용할 납기일을 먼저 선택하세요.';date.focus();return;}
  const inputs=rows.querySelectorAll('[data-field="requested_due"]');
  if(!inputs.length){status.textContent='먼저 품목을 추가하세요.';return;}
  bulkDue=date.value;inputs.forEach(input=>input.value=bulkDue);
  status.textContent=`${inputs.length}개 품목에 ${bulkDue} 적용했습니다. PO 저장을 누르면 반영됩니다.`;
 };
 if(data.revision_lines){
  const attachMapping=row=>{const label=document.createElement('label');label.textContent='기존 품목 연결';const select=document.createElement('select');select.dataset.lineMapping='true';select.add(new Option('신규 품목 (기존 배정 품목은 별도 유지 필요)',''));for(const line of data.revision_lines)select.add(new Option(line.label,line.id));select.value=row.dataset.id||'';select.onchange=()=>{row.dataset.id=select.value;const matched=data.revision_lines.find(line=>line.id===select.value);const internal=row.querySelector('[data-field="internal_name"]');if(matched&&internal){internal.value=matched.internal_name||'';internal.dispatchEvent(new Event('input',{bubbles:true}));}};label.append(select);if(tableMode){const cell=document.createElement('td');cell.append(label);row.append(cell);}else row.prepend(label);};
  rows.querySelectorAll('.line-row').forEach(attachMapping);
  const add=document.querySelector('#add-line');add.onclick=()=>{addLine();attachMapping(rows.lastElementChild);};
 }
 orderForm.elements.customer_id.addEventListener('change',e=>{const opt=e.target.selectedOptions[0];if(opt.dataset.type)orderForm.elements.order_type.value=opt.dataset.type;if(opt.dataset.currency)rows.querySelectorAll('[data-field="currency"]').forEach(el=>el.value=opt.dataset.currency);});
 document.querySelector('#add-customer').onclick=async()=>{const button=document.querySelector('#add-customer');if(button.disabled)return;button.disabled=true;try{const result=await postJson('/customers/',{name:document.querySelector('#customer-name').value,default_type:document.querySelector('#customer-type').value,currency:document.querySelector('#customer-currency').value});const select=orderForm.elements.customer_id;let option=[...select.options].find(item=>item.value===result.id);if(!option){option=new Option(result.name,result.id);select.add(option);}option.dataset.type=result.default_type;option.dataset.currency=result.currency;select.value=result.id;orderForm.elements.customer_id.dispatchEvent(new Event('change'));}catch(e){showError(e);}finally{button.disabled=false;}};
 orderForm.onsubmit=async e=>{e.preventDefault();const button=orderForm.querySelector('[type="submit"]');button.disabled=true;try{const payload=Object.fromEntries(new FormData(orderForm));payload.row_version=data.row_version;payload.lines=[...rows.querySelectorAll('.line-row')].map(row=>({id:row.dataset.id,...Object.fromEntries([...row.querySelectorAll('[data-field]')].map(el=>[el.dataset.field,el.dataset.field==='quantity'?el.value.replaceAll(',',''):el.value]))}));const result=await postJson(orderForm.dataset.url,payload);location.href=result.url;}catch(error){showError(error);button.disabled=false;}};
}
for(const form of document.querySelectorAll('[data-shipment-form]'))form.onsubmit=async e=>{e.preventDefault();try{const payload={...Object.fromEntries(new FormData(form)),id:form.dataset.id,row_version:Number(form.dataset.version),allocations:Object.fromEntries([...form.querySelectorAll('[data-allocation]')].map(el=>[el.dataset.allocation,el.value]))};await postJson(form.dataset.correct?`/shipments/${form.dataset.id}/correct/`:`/orders/${form.dataset.order}/shipments/`,payload);location.reload();}catch(error){showError(error);}};
for(const button of document.querySelectorAll('[data-confirm-shipment]'))button.onclick=async()=>{try{await postJson(`/shipments/${button.dataset.confirmShipment}/confirm/`,{row_version:Number(button.dataset.version)});location.reload();}catch(error){showError(error);}};
for(const form of document.querySelectorAll('[data-cancel-line]'))form.onsubmit=async e=>{e.preventDefault();try{await postJson(`/lines/${form.dataset.cancelLine}/cancel-remaining/`,{quantity:form.elements.quantity.value,row_version:Number(form.dataset.version)});location.reload();}catch(error){showError(error);}};
for(const button of document.querySelectorAll('[data-cancel-order]'))button.onclick=async()=>{if(!confirm('PO를 취소하고 미완료 업무를 취소할까요? 완료 기록은 유지됩니다.'))return;try{await postJson(`/orders/${button.dataset.cancelOrder}/cancel/`,{row_version:Number(button.dataset.version)});location.reload();}catch(error){showError(error);}};
for(const form of document.querySelectorAll('[data-cancel-shipment]'))form.onsubmit=async e=>{e.preventDefault();try{await postJson(`/shipments/${form.dataset.cancelShipment}/cancel/`,{reason:form.elements.reason.value,row_version:Number(form.dataset.version)});location.reload();}catch(error){showError(error);}};
for(const form of document.querySelectorAll('[data-update-eta]'))form.onsubmit=async e=>{e.preventDefault();try{await postJson(`/shipments/${form.dataset.updateEta}/eta/`,{eta:form.elements.eta.value,row_version:Number(form.dataset.version)});location.reload();}catch(error){showError(error);}};
for(const button of document.querySelectorAll('[data-delete-order]'))button.onclick=async()=>{
 if(!confirm((button.dataset.poNumber?`PO ${button.dataset.poNumber}\n`:'')+'이 PO 전체를 삭제하고 휴지통으로 이동할까요? 모든 품목이 달력·알림에서 제외되며 원본과 이력은 보존됩니다.'))return;
 button.disabled=true;try{const result=await postJson(`/orders/${button.dataset.deleteOrder}/delete/`,{row_version:Number(button.dataset.version)});location.href=result.url;}catch(error){showError(error);button.disabled=false;}
};
for(const button of document.querySelectorAll('[data-restore-order]'))button.onclick=async()=>{
 button.disabled=true;try{const result=await postJson(`/orders/${button.dataset.restoreOrder}/restore/`,{row_version:Number(button.dataset.version)});location.href=result.url;}catch(error){showError(error);button.disabled=false;}
};

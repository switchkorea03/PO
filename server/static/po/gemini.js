import {postJson,escapeHtml as esc} from './api.js';
const panel=document.querySelector('[data-gemini-panel]');
if(panel){
 const consent=panel.querySelector('[data-gemini-consent]'),analyze=panel.querySelector('[data-gemini-analyze]'),apply=panel.querySelector('[data-gemini-apply]');
 const status=panel.querySelector('[data-gemini-status]'),preview=panel.querySelector('[data-gemini-proposal]'),actions=panel.querySelector('[data-gemini-actions]');
 const base=`/intake/${panel.dataset.draftId}/gemini/`,version=Number(panel.dataset.draftVersion);let reviewId=null,busy=false;
 const value=field=>field?.value??'미인식';
 const number=field=>{const raw=value(field);const [whole,fraction]=String(raw).split('.');return whole.replace(/\B(?=(\d{3})+(?!\d))/g,',')+(fraction!==undefined?`.${fraction}`:'');};
 consent?.addEventListener('change',()=>{analyze.disabled=!consent.checked||busy;});
 analyze?.addEventListener('click',async()=>{
  if(busy||!consent.checked)return;busy=true;analyze.disabled=true;apply.disabled=true;actions.hidden=true;preview.hidden=true;reviewId=null;
  status.textContent='Gemini가 문서를 읽고 있습니다. 최대 60초 정도 걸릴 수 있습니다.';
  try{
   const data=await postJson(base,{draft_version:version,consent:true});reviewId=data.review_id;
   const proposal=data.proposal,fields=proposal.fields;
   const labels=[['customer_name','고객'],['po_number','PO번호'],['order_type','국내/해외'],['ordered_on','발주일'],['contact','담당자']];
   const cell=(text)=>`<td>${esc(text)}</td>`;
   preview.innerHTML=`<h3>AI 제안 · 원본과 비교하세요</h3><div style="overflow-x:auto"><table><thead><tr>${labels.map(([,label])=>`<th>${esc(label)}</th>`).join('')}</tr></thead><tbody><tr>${labels.map(([key])=>cell(key==='order_type'?({'domestic':'국내','overseas':'해외'}[value(fields[key])]||'미인식'):value(fields[key]))).join('')}</tr></tbody></table><table><thead><tr>${['자사품목명','고객품목명','스펙','수량','단위','단가','통화','공급가액','납기일'].map(label=>`<th>${label}</th>`).join('')}</tr></thead><tbody>${proposal.lines.map(line=>`<tr>${['internal_name','code','name','quantity','unit','unit_price','currency','source_amount','requested_due'].map(key=>cell(['quantity','unit_price','source_amount'].includes(key)?number(line[key]):value(line[key]))).join('')}</tr>`).join('')}</tbody></table></div><ul>${proposal.warnings.map(warning=>`<li>${esc(warning)}</li>`).join('')}</ul>`;
   preview.hidden=false;actions.hidden=false;apply.disabled=false;
   panel.querySelector('[data-gemini-used]').textContent=String(Math.max(0,Number(panel.dataset.dailyLimit)-data.remaining_today));
   status.textContent=`인식 보완 완료 · 사용 토큰 ${data.usage.total??0} · 오늘 앱에서 ${data.remaining_today}회 더 실행 가능. 아직 입력값에 적용되지 않았습니다.`;
  }catch(error){status.textContent=error.message+' 기존 입력값은 유지됩니다.';}
  finally{busy=false;analyze.disabled=!consent.checked;}
 });
 apply?.addEventListener('click',async()=>{
  if(busy||!reviewId)return;busy=true;apply.disabled=true;if(analyze)analyze.disabled=true;
  try{await postJson(`${base}${reviewId}/apply/`,{draft_version:version});location.reload();}
  catch(error){status.textContent=error.message;busy=false;apply.disabled=false;if(analyze)analyze.disabled=!consent.checked;}
 });
}

const fileInput=document.querySelector('[data-upload-file]');
const zone=document.querySelector('[data-drop-zone]');
if(fileInput&&zone){
 const hint=document.querySelector('[data-file-name]');
 const showFile=()=>{const file=fileInput.files[0];if(hint)hint.textContent=file?file.name+' · '+(file.size/1024/1024).toFixed(2)+' MB':'PDF · Excel(.xlsx/.xls)을 선택하세요.';};
 fileInput.addEventListener('change',showFile);
 for(const name of ['dragenter','dragover'])zone.addEventListener(name,e=>{e.preventDefault();zone.classList.add('dragging');});
 for(const name of ['dragleave','drop'])zone.addEventListener(name,e=>{e.preventDefault();zone.classList.remove('dragging');});
 zone.addEventListener('drop',e=>{if(e.dataTransfer.files.length){const transfer=new DataTransfer();transfer.items.add(e.dataTransfer.files[0]);fileInput.files=transfer.files;showFile();}});
 const form=fileInput.form;
 form?.addEventListener('submit',()=>{const button=form.querySelector('[type=submit]');if(button){button.disabled=true;button.textContent='업로드 중…';}});
}
// Preserve ordinary navigation and server form validation when JavaScript is absent.
for(const link of document.querySelectorAll('[data-scroll-section]'))link.addEventListener('click',()=>{document.querySelector(link.hash)?.setAttribute('tabindex','-1');});

const preview=document.querySelector('[data-pdf-preview]');
if(preview){
 const image=preview.querySelector('[data-pdf-image]');
 const status=preview.querySelector('[data-pdf-status]');
 const previous=preview.querySelector('[data-pdf-previous]');
 const next=preview.querySelector('[data-pdf-next]');
 let page=1,count=1,blobUrl=null;
 async function load(number){
  previous.disabled=true;next.disabled=true;status.textContent='문서 미리보기 준비 중…';
  try{
   const response=await fetch(preview.dataset.pdfPreview+'?page='+number,{credentials:'same-origin'});
   if(!response.ok)throw Error('미리보기를 표시하지 못했습니다. 원본 다운로드로 확인하세요.');
   const blob=await response.blob();count=Number(response.headers.get('X-PDF-Page-Count'))||1;
   if(blobUrl)URL.revokeObjectURL(blobUrl);
   blobUrl=URL.createObjectURL(blob);image.src=blobUrl;image.hidden=false;page=number;
   image.alt='PO 원본 PDF '+page+'페이지';status.textContent=page+' / '+count+' 페이지';
   previous.disabled=page<=1;next.disabled=page>=count;
  }catch(error){image.hidden=true;status.textContent=error.message;}
 }
 previous.addEventListener('click',()=>load(page-1));next.addEventListener('click',()=>load(page+1));
 load(1);
}

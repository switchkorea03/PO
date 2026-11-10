const dialog=document.querySelector('[data-calendar-dialog]');
if(dialog){
 const open=()=>{if(location.hash==='#day-agenda'&&!dialog.open)dialog.showModal();};
 const close=()=>dialog.close();
 dialog.querySelector('[data-calendar-close]').addEventListener('click',close);
 dialog.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)close();}});
 dialog.addEventListener('close',()=>{if(location.hash==='#day-agenda')history.replaceState(null,'',location.pathname+location.search);});
 window.addEventListener('hashchange',open);
 open();
}

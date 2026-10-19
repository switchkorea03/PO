const {chromium}=require('../../server/e2e/node_modules/playwright');
const assert=require('node:assert/strict');
const {resolve}=require('node:path');
const root=resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch();let checks=0;
 try{
  for(const width of [1440,1280,768,360]){
   const context=await browser.newContext({viewport:{width,height:1000}});
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto('http://127.0.0.1:4174/');await page.waitForLoadState('networkidle');
   await page.getByRole('heading',{name:'업무 달력',exact:true}).waitFor();
   for(const route of ['calendar','orders','orders/bj','upload','settings','history','users','guide']){
    await page.goto('http://127.0.0.1:4174/#/'+route);await page.waitForLoadState('networkidle');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`Overflow at ${width} ${route}`);checks++;
   }
   await page.goto('http://127.0.0.1:4174/#/calendar');
   const erp=page.locator('[data-task]').filter({hasText:'알파컴포넌트'}).filter({hasText:'ERP 2개 처리'});
   await erp.click();await page.locator('[data-step="1"]').check();
   assert.equal(await page.locator('.drawer [data-step]:checked').count(),2);checks++;
   await page.getByRole('button',{name:'닫기',exact:true}).click();
   await page.locator('[data-task]').filter({hasText:'비나일렉트로닉스'}).filter({hasText:'인보이스+ERP'}).click();
   await page.locator('#move-form [name=date]').fill('2026-10-20');await page.getByRole('button',{name:'업무일 저장',exact:true}).click();
   await page.reload();await page.getByRole('button',{name:'2026-10-20 업무 선택'}).click();
   await page.locator('[data-task]').filter({hasText:'비나일렉트로닉스'}).filter({hasText:'인보이스+ERP'}).click();
   assert.equal(await page.locator('#move-form [name=date]').inputValue(),'2026-10-20');checks++;
   await page.goto('http://127.0.0.1:4174/#/orders/vn');await page.getByRole('button',{name:'날짜·수량 수정',exact:true}).click();
   await page.locator('#shipment-form [name=etd]').fill('2026-10-17');await page.locator('#shipment-form button[type=submit],#shipment-form .primary').click();
   await page.getByRole('button',{name:/업무 5/}).click();
   await page.locator('[data-task]').filter({hasText:'ERP 2개 처리'}).click();
   assert.match(await page.locator('.drawer').textContent(),/2026-10-19/);checks++;
   await page.goto('http://127.0.0.1:4174/#/orders/bj');await page.getByRole('button',{name:'품목·출고',exact:true}).click();assert.match(await page.locator('.detail-meta').textContent(),/30 EA/);checks++;
   if(width===1440){await page.screenshot({path:resolve(root,'preview-po.png'),fullPage:true});}
   await page.getByRole('button',{name:'+ 회차 추가',exact:true}).click();await page.locator('#shipment-form [name=qty]').fill('1');await page.locator('#shipment-form .primary').click();
   assert.match(await page.locator('#toast').textContent(),/초과/);checks++;
   await page.goto('http://127.0.0.1:4174/#/upload');await page.locator('#review-form [name=po]').fill('TEST-'+width);await page.locator('#review-form button[type=submit]').click();await page.waitForURL(/#\/orders\/demo/);checks++;
   await page.goto('http://127.0.0.1:4174/#/calendar');const customerNames=await page.locator('#customer-filter option').allTextContents();assert.equal(new Set(customerNames).size,customerNames.length);checks++;
   await page.evaluate(()=>localStorage.clear());await page.goto('http://127.0.0.1:4174/#/calendar');await page.reload();
   if(width===1440||width===360)await page.screenshot({path:resolve(root,width===1440?'preview-desktop.png':'preview-mobile.png'),fullPage:true});
   assert.deepEqual(errors,[],`Browser errors at ${width}`);
   await context.close();console.log(`Viewport ${width}: routes and interactions verified`);
  }
  console.log(`${checks} browser checks passed`);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});

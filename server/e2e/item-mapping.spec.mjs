import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';

const pairs=[['MESA100005A','JT1138BEM'],['MESA100007A','JT1140WJ-BEM'],['MESA100008A','JTP1169BEM'],['MESAH00002A','JT1280A6']];
test('reference image mappings autofill in manual entry and file review, and persist',async({page},info)=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 await page.goto('/orders/new/');
 await expect(page.getByLabel('ERP 거래유형',{exact:true})).toHaveCount(0);
 await expect(page.getByLabel('PO 수령일',{exact:true})).toHaveCount(0);
 if(info.project.name==='desktop'){
  const boxes=await page.locator('.po-basic-grid > label').evaluateAll(labels=>labels.map(label=>label.getBoundingClientRect().y));
  expect(boxes).toHaveLength(6);expect(Math.max(...boxes)-Math.min(...boxes)).toBeLessThan(3);
 }
 await expect(page.getByLabel('고객품목명',{exact:true})).toBeVisible();
 await expect(page.getByLabel('스펙',{exact:true})).toBeVisible();
 for(const [code,internal] of pairs){
  await page.locator('[data-field=name]').fill(code);
  await expect(page.locator('[data-field=internal_name]')).toHaveValue(internal);
 }
 const fixture=join(mkdtempSync(join(tmpdir(),'po-item-map-')),'mapping.xlsx');
 const number=`ITEM-MAP-${info.project.name}-${Date.now()}`;
 execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"from openpyxl import Workbook;import sys,json;w=Workbook();s=w.active;s.append(['고객명','범진전자']);s.append(['PO 번호',sys.argv[2]]);s.append(['품목코드','품명','수량','단위','단가','통화','납기일']);[s.append([c,c,1000,'EA',1500,'KRW','2026-10-29']) for c,n in json.loads(sys.argv[3])];w.save(sys.argv[1])",fixture,number,JSON.stringify(pairs)]);
 await page.goto('/intake/upload/');await page.getByLabel('PO 파일',{exact:true}).setInputFiles(fixture);await page.getByRole('button',{name:'업로드·인식',exact:true}).click();
 await expect(page).toHaveURL(/\/intake\/[0-9a-f-]+\/review\/$/);
 const table=page.getByRole('table',{name:'PO 품목 정보 편집'});
 await expect(table).toBeVisible();
 await expect(table.getByRole('columnheader')).toHaveText(['자사품목명','고객품목명','스펙','수량','단위','단가','통화','공급가액','납기일','관리']);
 const first=table.locator('.line-row').first();
 await expect(table.locator('[data-po-number]')).toHaveCount(0);
 await expect(first.locator('[data-field=name]')).toBeVisible();
 await first.locator('[data-field=source_amount]').fill('1500000');
 await expect(first.locator('[data-field=quantity]')).toHaveValue('1,000');
 await first.locator('[data-field=quantity]').fill('1234567.8901234567');
 await first.locator('[data-field=quantity]').press('Tab');
 await expect(first.locator('[data-field=quantity]')).toHaveValue('1,234,567.8901234567');
 const boxes=await Promise.all(['[data-field=code]','[data-field=internal_name]','[data-field=name]','[data-field=quantity]','[data-field=unit]','[data-field=unit_price]','[data-field=currency]','[data-field=source_amount]','[data-field=requested_due]'].map(selector=>first.locator(selector).boundingBox()));
 expect(Math.max(...boxes.map(box=>box.y))-Math.min(...boxes.map(box=>box.y))).toBeLessThan(3);
 const layout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,blocks:['main','.review-heading','#order-form','.po-review-wrap','.po-review-table'].map(selector=>{const e=document.querySelector(selector),b=e.getBoundingClientRect();return {selector,width:b.width,right:b.right,overflow:getComputedStyle(e).overflowX};})}));
 expect(layout.scroll,JSON.stringify(layout)).toBeLessThanOrEqual(layout.width);
 await page.screenshot({path:resolve(`../../.runtime/2026-10-27-po-review-${info.project.name}.png`),fullPage:true});
 for(let i=0;i<pairs.length;i++)await expect(page.locator('.line-row').nth(i).locator('[data-field=internal_name]')).toHaveValue(pairs[i][1]);
 await page.locator('[name=customer_id]').selectOption({label:'범진전자'});
 const saved=page.waitForRequest(request=>request.method()==='POST'&&request.url().endsWith('/confirm/'));
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);
 expect((await saved).postDataJSON().lines[0].quantity).toBe('1234567.8901234567');
 const detail=page.url();await page.goto('/orders/');
 const rows=page.getByRole('row').filter({hasText:number});await expect(rows).toHaveCount(4);
 for(const [code,internal] of pairs)await expect(rows.filter({hasText:code})).toContainText(internal);
 await page.goto(detail+'edit/');
 await expect(page.locator('.line-row').filter({has:page.locator('[data-field=code][value="MESA100005A"]')}).locator('[data-field=quantity]')).toHaveValue('1,234,567.8901234567');
 for(const [code,internal] of pairs){const row=page.locator('.line-row').filter({has:page.locator(`[data-field=name][value="${code}"]`)});await expect(row.locator('[data-field=internal_name]')).toHaveValue(internal);}
});

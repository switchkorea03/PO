import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';

test('production frontend navigation and protected PDF review',async({page},info)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 for(const route of ['/calendar/','/orders/','/orders/new/','/intake/upload/','/settings/notices/','/notices/history/']){
  await page.goto(route);await page.waitForLoadState('networkidle');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),route+' should fit viewport').toBeTruthy();
  await expect(page.locator('nav[aria-label="주 메뉴"] [aria-current="page"]')).toHaveCount(1);
 }
 await page.goto('/calendar/');await expect(page.locator('.summary-card')).toHaveCount(4);
 await page.screenshot({path:resolve('../../.runtime/frontend-'+info.project.name+'.png'),fullPage:true});
 const directory=mkdtempSync(join(tmpdir(),'po-frontend-'));const fixture=join(directory,'review.pdf');
 try{
  execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"from reportlab.pdfgen import canvas;import sys;c=canvas.Canvas(sys.argv[1]);c.drawString(40,800,'PO No: REVIEW-'+sys.argv[2]);c.drawString(40,780,'Item Code | Name | Quantity | Unit | Price | Currency | Due Date');c.drawString(40,760,'PART-1 | Component | 100 | EA | 0.2 | USD | 2026-10-23');c.save()",fixture,info.project.name]);
  await page.goto('/intake/upload/');await page.getByLabel('PO 파일',{exact:true}).setInputFiles(fixture);await page.getByRole('button',{name:'업로드·인식',exact:true}).click();
  await expect(page).toHaveURL(/\/intake\/[0-9a-f-]+\/review\/$/,{timeout:40000});await page.waitForLoadState('networkidle');
  await expect(page.locator('[data-pdf-image]')).toBeVisible();await expect.poll(()=>page.locator('[data-pdf-image]').evaluate(img=>img.naturalWidth)).toBeGreaterThan(0);
  const url=await page.locator('[data-pdf-preview]').getAttribute('data-pdf-preview');const response=await page.request.get(url);
  expect(response.status()).toBe(200);expect(response.headers()['content-type']).toBe('image/png');expect(response.headers()['cross-origin-resource-policy']).toBe('same-origin');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await expect(page.locator('[data-field=quantity]').first()).toHaveValue('100');
  await page.screenshot({path:resolve('../../.runtime/frontend-review-'+info.project.name+'.png'),fullPage:true});
 }finally{rmSync(directory,{recursive:true,force:true});}
 expect(errors).toEqual([]);
});

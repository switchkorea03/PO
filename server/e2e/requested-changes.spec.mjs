import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';

async function login(page){await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');}

test('six requested improvements: item names, thousands, customer groups, one-row list and recoverable delete',async({page},info)=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));await login(page);await page.goto('/orders/new/');
 for(const [name,kind] of [['범진전자','domestic'],['SJI','domestic'],['SJIT','domestic'],['켐트로비나','overseas'],['솔루엠','overseas'],['리모트솔루션','overseas']]) await expect(page.locator('[name=customer_id] option').filter({hasText:new RegExp(`^${name}$`)})).toHaveAttribute('data-type',kind);
 await page.locator('[name=customer_id]').selectOption({label:'범진전자'});
 const number=`UI-6-${info.project.name}-${Date.now()}`;await page.locator('[name=po_number]').fill(number);
 await page.locator('[data-field=code]').fill('MESA100005A');await page.locator('[data-field=name]').fill('MESA100005A');await expect(page.locator('[data-field=internal_name]')).toHaveValue('JT1138BEM');
 await page.locator('[data-field=quantity]').fill('12000');await page.locator('[data-field=unit_price]').fill('1500');await page.locator('[data-field=requested_due]').fill('2026-10-29');
 await expect(page.locator('[data-item-name]')).toContainText('MESA100005A (JT1138BEM)');await expect(page.locator('[data-item-name]')).toContainText('12,000');
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);
 const orderUrl=page.url();await expect(page.getByTestId('remaining')).toContainText('12,000');
 await page.goto('/orders/');const row=page.getByRole('row').filter({hasText:number});await expect(row).toHaveCount(1);
 for(const value of ['MESA100005A','JT1138BEM','12,000 EA','1,500','18,000,000']) await expect(row).toContainText(value);
 await expect(row.locator('[name=requested_due]')).toHaveValue('2026-10-29');
 for(const label of ['발주서 등록일','PO 번호','고객품목명','수량','단가','공급가액','납기일'])await expect(page.getByRole('columnheader',{name:label,exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:resolve(`../../.runtime/2026-10-27-po-list-${info.project.name}.png`),fullPage:true});
 page.once('dialog',dialog=>dialog.accept());await row.getByRole('button',{name:'삭제',exact:true}).click();await expect(row).toHaveCount(0);
 await page.goto('/orders/?state=deleted');const deleted=page.getByRole('row').filter({hasText:number});await expect(deleted).toBeVisible();await deleted.getByRole('button',{name:'복원',exact:true}).click();await expect(page).toHaveURL(orderUrl);await expect(page.getByTestId('remaining')).toContainText('12,000');expect(errors).toEqual([]);
});

test('PNG upload uses local OCR and shows authenticated source preview',async({page},info)=>{
 test.setTimeout(120000);await login(page);
 const directory=mkdtempSync(join(tmpdir(),'po-png-check-'));const fixture=join(directory,'po.png');const number='PNG-100';
 execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"from PIL import Image,ImageDraw,ImageFont;import sys;im=Image.new('RGB',(1800,900),'white');d=ImageDraw.Draw(im);f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',50);d.text((80,100),'PO No: '+sys.argv[2],font=f,fill='black');im.save(sys.argv[1])",fixture,number]);
 await page.goto('/intake/upload/');await expect(page.locator('[data-upload-file]')).toHaveAttribute('accept',/\.png/);await page.getByLabel('PO 파일',{exact:true}).setInputFiles(fixture);await page.getByRole('button',{name:'업로드·인식',exact:true}).click();
 await expect(page).toHaveURL(/\/intake\/[0-9a-f-]+\/review\/$/,{timeout:110000});await expect(page.locator('.png-source-image')).toBeVisible();await expect(page.locator('[name=po_number]')).toHaveValue(number);
 const src=await page.locator('.png-source-image').getAttribute('src');const response=await page.request.get(src);expect(response.status()).toBe(200);expect(response.headers()['content-type']).toBe('image/png');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();await page.screenshot({path:resolve(`../../.runtime/2026-10-27-png-review-${info.project.name}.png`),fullPage:true});
 // Preserve the generated fixture for this run; no user-provided image is modified.
});

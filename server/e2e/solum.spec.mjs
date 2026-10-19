import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';

test('Solum PDF review keeps wrapped quantity and overseas defaults',async({page},info)=>{
 const directory=mkdtempSync(join(tmpdir(),'solum-po-'));const file=join(directory,'solum.pdf');
 try{
  execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"import sys;sys.path.insert(0,'..');from intake.tests.test_solum import solum_pdf;solum_pdf(sys.argv[1],po=sys.argv[2])",file,'SOL-UI-'+info.project.name]);
  await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
  await page.goto('/intake/upload/');await page.getByLabel('PO 파일',{exact:true}).setInputFiles(file);await page.getByRole('button',{name:'업로드·인식',exact:true}).click();
  await expect(page).toHaveURL(/\/intake\/[0-9a-f-]+\/review\/$/,{timeout:40000});await page.waitForLoadState('networkidle');
  await expect(page.locator('[data-field=quantity]').first()).toHaveValue('1080000.00');
  await expect(page.locator('[data-field=unit_price]').first()).toHaveValue('0.04150');
  await expect(page.locator('[data-field=currency]').first()).toHaveValue('USD');
  await expect(page.locator('[data-field=requested_due]').first()).toHaveValue('2026-10-20');
  await expect(page.locator('#order-form [name=order_type]')).toHaveValue('overseas');
  if(!await page.locator('#order-form [name=customer_id]').inputValue()){
   await expect(page.getByLabel('새 고객명',{exact:true})).toHaveValue('솔루엠(베트남향)');
   await expect(page.locator('#customer-type')).toHaveValue('overseas');
   await expect(page.locator('#customer-currency')).toHaveValue('USD');
   await page.getByRole('button',{name:'고객 추가',exact:true}).click();
   await expect(page.locator('#order-form [name=customer_id]')).not.toHaveValue('');
  }
  await expect(page.locator('[data-field=currency]').first()).toHaveValue('USD');
  await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);
  await expect(page.locator('[data-shipment-form] [name=etd]').first()).toHaveValue('');
  await expect(page.locator('main')).toContainText('해외');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 }finally{rmSync(directory,{recursive:true,force:true});}
});

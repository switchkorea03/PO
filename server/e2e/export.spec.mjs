import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

test('filtered PO list downloads a real Excel workbook',async({page},info)=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 await page.goto('/orders/new/');await page.locator('[name=customer_id]').selectOption({label:'범진전자'});
 const number=`EXPORT-${info.project.name}-${Date.now()}`;await page.locator('[name=po_number]').fill(number);
 await page.locator('[data-field=code]').fill('EXPORT-ITEM');await page.locator('[data-field=name]').fill('엑셀 다운로드 검증');
 await page.locator('[data-field=quantity]').fill('12345');await page.locator('[data-field=unit_price]').fill('2');await page.locator('[data-field=requested_due]').fill('2026-10-29');
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);
 await page.goto('/orders/?q='+encodeURIComponent(number)+'&type=domestic');
 const link=page.getByRole('link',{name:'엑셀 다운로드',exact:true});await expect(link).toBeVisible();
 const url=new URL(await link.getAttribute('href'),page.url());expect(url.searchParams.get('q')).toBe(number);expect(url.searchParams.get('type')).toBe('domestic');
 const pending=page.waitForEvent('download');await link.click();const download=await pending;expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
 const path=resolve(`../../.runtime/po-list-export-${info.project.name}.xlsx`);await download.saveAs(path);
 const result=JSON.parse(execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"from openpyxl import load_workbook;import sys,json;w=load_workbook(sys.argv[1]);s=w.active;print(json.dumps({'rows':s.max_row,'po':s['D2'].value,'quantity':s['H2'].value,'amount':s['K2'].value,'filter':s.auto_filter.ref}));w.close()",path],{encoding:'utf8'}));
 expect(result).toEqual({rows:2,po:number,quantity:12345,amount:24690,filter:'A1:P2'});
 await expect(page.getByRole('heading',{name:'PO 목록',exact:true})).toBeVisible();
});

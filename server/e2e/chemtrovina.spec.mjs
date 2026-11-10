import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';

test('CHEMTROVINA PDF fills PO basic information and five item rows',async({page},info)=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 const fixture=join(mkdtempSync(join(tmpdir(),'chem-po-')),'purchase-order.pdf');const number=`CHEM-${info.project.name}-${Date.now()}`;
 execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"import sys;sys.path.insert(0,sys.argv[3]);from intake.tests.test_chemtrovina import TEXT;from reportlab.pdfgen import canvas;p=canvas.Canvas(sys.argv[1],pagesize=(600,850));p.setFont('Helvetica',9);[p.drawString(25,825-i*13,t.replace('4600000001',sys.argv[2])) for i,t in enumerate(TEXT)];p.save()",fixture,number,resolve('..')]);
 await page.goto('/intake/upload/');await page.getByLabel('PO 파일',{exact:true}).setInputFiles(fixture);await page.getByRole('button',{name:'업로드·인식',exact:true}).click();await expect(page).toHaveURL(/\/intake\/[0-9a-f-]+\/review\/$/);
 await expect(page.locator('[name=po_number]')).toHaveValue(number);await expect(page.locator('[name=ordered_on]')).toHaveValue('2026-10-13');
 await expect(page.locator('[name=customer_id] option:checked')).toHaveText('켐트로비나');await expect(page.locator('[name=order_type]')).toHaveValue('overseas');await expect(page.locator('[name=contact]')).toHaveValue('Pur TEST BUYER');
 await expect(page.locator('.line-row')).toHaveCount(5);
 await expect(page.getByRole('table',{name:'PO 품목 정보 편집'}).getByRole('columnheader')).toHaveText(['자사품목명','고객품목명','스펙','수량','단위','단가','통화','공급가액','납기일','관리']);
 for(const [index,model] of ['JT1140WJ-BEM','JES1612GWAS','JS1267EM'].entries())await expect(page.locator('.line-row').nth(index).locator('[data-field=internal_name]')).toHaveValue(model);
 const first=page.locator('.line-row').first();await expect(first.locator('[data-field=code]')).toHaveValue('M01340001A');await expect(first.locator('[data-field=quantity]')).toHaveValue('4,000');await expect(first.locator('[data-field=unit_price]')).toHaveValue('0.0189');await expect(first.locator('[data-field=source_amount]')).toHaveValue('75.6');await expect(first.locator('[data-field=currency]')).toHaveValue('USD');await expect(first.locator('[data-field=requested_due]')).toHaveValue('2027-01-04');
 await page.getByLabel('전체 품목 납기일',{exact:true}).fill('2026-12-31');await page.getByRole('button',{name:'전체 품목에 적용',exact:true}).click();
 for(const input of await page.locator('[data-field=requested_due]').all())await expect(input).toHaveValue('2026-12-31');
 await page.screenshot({path:resolve(`../../.runtime/chemtrovina-review-${info.project.name}.png`),fullPage:true});
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);const detail=page.url();await page.goto(detail+'edit/');
 for(const input of await page.locator('[data-field=requested_due]').all())await expect(input).toHaveValue('2026-12-31');
});

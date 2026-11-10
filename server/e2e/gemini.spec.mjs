import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';

test('Gemini proposal is opt-in, preserves current inputs until Apply, then saves through normal PO form',async({page},info)=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 const fixture=join(mkdtempSync(join(tmpdir(),'ai-po-')),'synthetic-po.pdf');const number=`AI-LOCAL-${info.project.name}-${Date.now()}`;
 execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"import sys;sys.path.insert(0,sys.argv[3]);from intake.tests.test_chemtrovina import TEXT;from reportlab.pdfgen import canvas;p=canvas.Canvas(sys.argv[1],pagesize=(600,850));p.setFont('Helvetica',9);[p.drawString(25,825-i*13,t.replace('4600000001',sys.argv[2])) for i,t in enumerate(TEXT)];p.save()",fixture,number,resolve('..')]);
 await page.goto('/intake/upload/');await page.getByLabel('PO 파일',{exact:true}).setInputFiles(fixture);await page.getByRole('button',{name:'업로드·인식',exact:true}).click();await expect(page).toHaveURL(/\/intake\/[0-9a-f-]+\/review\/$/);
 const reviewUrl=page.url();const panel=page.locator('[data-gemini-panel]');
 const run=page.getByRole('button',{name:'Gemini로 인식 보완',exact:true});await expect(run).toBeDisabled();
 await expect(panel).toContainText('Google');await expect(page.locator('[name=po_number]')).toHaveValue(number);
 await panel.locator('[data-gemini-consent]').check();await run.click();await expect(panel.locator('[data-gemini-proposal]')).toBeVisible();
 await expect(panel).toContainText('AI-001');await expect(panel).toContainText('1,000');await expect(page.locator('[name=po_number]')).toHaveValue(number);await expect(page.locator('.line-row')).toHaveCount(5);
 expect(await page.content()).not.toContain('e2e-stub-never-a-real-key');
 // Reload must retain the review context/query string after explicit Apply.
 await page.evaluate(()=>history.replaceState(null,'',location.href+'?context=preserved'));
 await page.getByRole('button',{name:'AI 제안 적용',exact:true}).click();await page.waitForURL(reviewUrl+'?context=preserved');
 await expect(page.locator('[name=po_number]')).toHaveValue('AI-001');await expect(page.locator('.line-row')).toHaveCount(1);
 await expect(page.locator('[data-field=internal_name]')).toHaveValue('JES1612GWAS');await expect(page.locator('[data-field=quantity]')).toHaveValue('1,000');
 await page.screenshot({path:resolve(`../../.runtime/gemini-review-${info.project.name}.png`),fullPage:true});
 await page.locator('[name=po_number]').fill(`AI-SAVED-${info.project.name}-${Date.now()}`);await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);
 await page.goto(page.url()+'edit/');await expect(page.locator('[data-field=internal_name]')).toHaveValue('JES1612GWAS');await expect(page.locator('[data-field=requested_due]')).toHaveValue('2026-12-01');
});

import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';
test('Excel upload is extracted and corrected before registration',async({page},info)=>{
 const fixture=resolve('test-upload-'+info.project.name+'.xlsx');
 execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"from openpyxl import Workbook;import sys;w=Workbook();s=w.active;s.append(['PO 번호','FILE-1']);s.append(['품목코드','품명','수량','단위','납기일']);s.append(['PART-1','Sample Part',100,'EA','2026-10-19']);w.save(sys.argv[1])",fixture]);
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();
 await page.goto('/intake/upload/');await page.getByLabel('PO 파일',{exact:true}).setInputFiles(fixture);await page.getByRole('button',{name:'업로드·인식',exact:true}).click();
 await expect(page).toHaveURL(/\/intake\/[0-9a-f-]+\/review\/$/,{timeout:40000});
 await expect(page.getByRole('heading',{name:'원본과 인식값 확인'})).toBeVisible();
 await expect(page.locator('[data-field="quantity"]').first()).toHaveValue('100');
 await page.getByLabel('새 고객명').fill('파일고객-'+info.project.name);await page.getByRole('button',{name:'고객 추가',exact:true}).click();await expect(page.locator('[name=customer_id]')).not.toHaveValue('');
 await page.getByLabel('PO 번호',{exact:true}).fill('FILE-'+info.project.name);await page.locator('[data-field="quantity"]').first().fill('70');await page.getByRole('button',{name:'PO 저장',exact:true}).click();
 await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);await expect(page.getByTestId('remaining').first()).toContainText('70');await expect(page.getByRole('heading',{name:'원본 파일',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';

test('reuploading a trashed PO requires editing and saving; active duplicates remain blocked',async({page},info)=>{
 await page.goto('/accounts/login/');
 await page.getByLabel('사용자 이름').fill('e2e-manager');
 await page.getByLabel('비밀번호').fill('local-e2e-password');
 await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 const number=`REUPLOAD-${info.project.name}-${Date.now()}`;
 const fixture=join(mkdtempSync(join(tmpdir(),'po-reupload-')),'po.xlsx');
 execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',"from openpyxl import Workbook;import sys;w=Workbook();s=w.active;s.append(['고객명','범진전자']);s.append(['PO 번호',sys.argv[2]]);s.append(['품목코드','품명','수량','단위','단가','통화','납기일']);s.append(['PART-1','재등록 검증',1000,'EA',1500,'KRW','2026-10-29']);w.save(sys.argv[1])",fixture,number]);
 const upload=async()=>{
  await page.goto('/intake/upload/');
  await page.getByLabel('PO 파일',{exact:true}).setInputFiles(fixture);
  await page.getByRole('button',{name:'업로드·인식',exact:true}).click();
 };
 await upload();await expect(page).toHaveURL(/\/intake\/[0-9a-f-]+\/review\/$/);
 await page.locator('[name=customer_id]').selectOption({label:'범진전자'});
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();
 await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);const original=page.url();
 await expect(page.locator('#shipments,#order-tasks')).toHaveCount(0);
 const cancel=async()=>{page.once('dialog',dialog=>dialog.accept());await page.locator('[data-cancel-order]').click();await expect(page.locator('main .warning')).toContainText('취소된 PO입니다.');};
 // A cancelled PO must reopen the registration form before restoring it.
 await cancel();await upload();await expect(page).toHaveURL(original+'reregister/');
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(original);
 const calendar=await(await page.request.get('/api/calendar/?start=2026-10-01&end=2026-10-31')).json();
 expect(calendar.tasks.some(task=>task.order_id===new URL(original).pathname.split('/')[2]&&task.state==='open')).toBeTruthy();
 // Reproduce the reported combination: cancelled first, then moved to trash.
 await cancel();
 await page.goto('/orders/');const rows=page.getByRole('row').filter({hasText:number});
 page.once('dialog',dialog=>dialog.accept());await rows.getByRole('button',{name:'삭제',exact:true}).click();await expect(rows).toHaveCount(0);
 await upload();await expect(page).toHaveURL(original+'reregister/');
 await expect(page.getByRole('heading',{name:'PO 재등록 정보 확인'})).toBeVisible();
 const editor=page.getByRole('table',{name:'PO 품목 정보 편집'});
 await expect(editor).toBeVisible();
 await expect(editor.getByRole('columnheader')).toHaveText(['자사품목명','고객품목명','스펙','수량','단위','단가','통화','공급가액','납기일','관리']);
 if(info.project.name==='desktop'){
  for(const selector of ['[data-field=code]','[data-field=internal_name]','[data-field=name]','[data-field=quantity]','[data-field=unit]','[data-field=unit_price]','[data-field=currency]','[data-field=source_amount]','[data-field=requested_due]']){
   const box=await editor.locator(selector).first().boundingBox();expect(box.x).toBeGreaterThanOrEqual(0);expect(box.x+box.width).toBeLessThanOrEqual(info.project.use.viewport.width);
  }
 }
 await expect(page.locator('[name=po_number]')).toHaveValue(number);
 await expect(page.locator('[data-field=quantity]')).toHaveValue('1,000');
 // Leaving the form without saving must not restore anything.
 await page.goto('/orders/');await expect(rows).toHaveCount(0);
 await page.goto('/orders/?state=deleted');await expect(page.getByRole('row').filter({hasText:number})).toHaveCount(1);
 await page.goto(original+'reregister/');await page.locator('[name=note]').fill('재등록 전 확인 완료');
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(original);
 await page.goto(original+'edit/');await expect(page.locator('[name=note]')).toHaveValue('재등록 전 확인 완료');
 await page.goto('/orders/');await expect(rows).toHaveCount(1);
 await page.goto('/orders/?state=deleted');await expect(page.getByRole('row').filter({hasText:number})).toHaveCount(0);
 await upload();await expect(page.getByRole('heading',{name:'이미 등록된 파일입니다'})).toBeVisible();
});

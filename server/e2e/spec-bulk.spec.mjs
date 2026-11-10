import {test,expect} from '@playwright/test';

const models=['JT1140WJ-BEM','JES1612GWAS','JS1267EM','JTP1135JEM','JT1126EM','JT1127WEM','JS6901EM','JT1136SHAEM','JT-S1102PEM','JT1152EM','JT1138FEM'];
test('spec auto naming and whole PO due date application preserve saved values and calendar',async({page},info)=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 await page.goto('/orders/new/');await page.locator('[name=customer_id]').selectOption({label:'범진전자'});
 const number=`BULK-${info.project.name}-${Date.now()}`;await page.locator('[name=po_number]').fill(number);
 const first=page.locator('.line-row').first();await first.locator('[data-field=code]').fill('CUSTOMER-1');
 for(const model of models){await first.locator('[data-field=name]').fill(`SWITCH;${model};TACT`);await expect(first.locator('[data-field=internal_name]')).toHaveValue(model);}
 for(const [spec,model] of [['SWITCH;SKRWAEE030;TACT','JTP1135JEM'],['JS6901; Slide Switch','JS6901'],['SKRWAEE030 / JTP1135JEM','JTP1135JEM'],['SWITCH;JS6901EM;TACT','JS6901EM']]){await first.locator('[data-field=name]').fill(spec);await expect(first.locator('[data-field=internal_name]')).toHaveValue(model);}
 await first.locator('[data-field=internal_name]').fill('MANUAL-PART');await first.locator('[data-field=name]').fill('SWITCH;JT1126EM;TACT');await expect(first.locator('[data-field=internal_name]')).toHaveValue('MANUAL-PART');
 await first.locator('[data-field=quantity]').fill('100');
 await page.getByRole('button',{name:'＋ 품목 추가',exact:true}).click();const second=page.locator('.line-row').nth(1);
 await second.locator('[data-field=code]').fill('CUSTOMER-2');await second.locator('[data-field=name]').fill('PUSH;JES1612GWAS;A');await second.locator('[data-field=quantity]').fill('100');await expect(second.locator('[data-field=internal_name]')).toHaveValue('JES1612GWAS');
 await page.getByLabel('전체 품목 납기일',{exact:true}).fill('2026-11-20');await page.getByRole('button',{name:'전체 품목에 적용',exact:true}).click();
 for(const input of await page.locator('[data-field=requested_due]').all())await expect(input).toHaveValue('2026-11-20');
 await page.getByRole('button',{name:'＋ 품목 추가',exact:true}).click();const extra=page.locator('.line-row').nth(2);await expect(extra.locator('[data-field=requested_due]')).toHaveValue('2026-11-20');await extra.locator('[data-remove-line]').click();
 await second.locator('[data-field=requested_due]').fill('2026-11-21');
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);const detail=page.url();const id=new URL(detail).pathname.split('/')[2];
 await page.goto(detail+'edit/');
 const savedFirst=page.locator('.line-row').filter({has:page.locator('[data-field=code][value="CUSTOMER-1"]')});await expect(savedFirst.locator('[data-field=internal_name]')).toHaveValue('MANUAL-PART');await expect(savedFirst.locator('[data-field=requested_due]')).toHaveValue('2026-11-20');
 await page.getByLabel('전체 품목 납기일',{exact:true}).fill('2026-11-24');await page.getByRole('button',{name:'전체 품목에 적용',exact:true}).click();await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(detail);
 const data=await(await page.request.get('/api/calendar/?start=2026-11-16&end=2026-11-27')).json();const tasks=data.tasks.filter(task=>task.order_id===id&&task.kind==='domestic_excel');expect(tasks.length).toBeGreaterThan(0);expect(tasks.every(task=>task.effective_on==='2026-11-24')).toBeTruthy();
});

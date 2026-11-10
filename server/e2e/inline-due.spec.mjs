import {test,expect} from '@playwright/test';
import {resolve} from 'node:path';

test('edit item due dates in PO list and count calendar work by company',async({page},info)=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 await page.goto('/orders/new/');await page.locator('[name=customer_id]').selectOption({label:'범진전자'});const customer=await page.locator('[name=customer_id]').inputValue();
 const number=`INLINE-${info.project.name}-${Date.now()}`;await page.locator('[name=po_number]').fill(number);await page.getByRole('button',{name:'＋ 품목 추가',exact:true}).click();
 for(let i=0;i<2;i++){
  const line=page.locator('.line-row').nth(i);await line.locator('[data-field=code]').fill('INLINE-'+i);await line.locator('[data-field=name]').fill('INLINE-'+i);
  await line.locator('[data-field=quantity]').fill('100');await line.locator('[data-field=requested_due]').fill('2026-11-17');
 }
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);const id=new URL(page.url()).pathname.split('/')[2];
 await page.goto('/orders/?q='+number+'&type=domestic');
 const rows=page.getByRole('row').filter({hasText:number});const first=rows.filter({hasText:'INLINE-0'});const second=rows.filter({hasText:'INLINE-1'});
 const update=async value=>{
  await first.locator('[name=requested_due]').fill(value);
  const response=page.waitForResponse(response=>response.request().method()==='POST'&&/\/lines\/[0-9a-f-]+\/due\/$/.test(new URL(response.url()).pathname));
  await first.getByRole('button',{name:'저장',exact:true}).click();expect((await response).status()).toBe(302);
  await expect(page.getByText('납기일을 저장했습니다.',{exact:true})).toBeVisible();await expect(first.locator('[name=requested_due]')).toHaveValue(value);
  expect(new URL(page.url()).searchParams.get('q')).toBe(number);
 };
 await update('2026-11-20');await expect(second.locator('[name=requested_due]')).toHaveValue('2026-11-17');
 let data=await(await page.request.get(`/api/calendar/?start=2026-11-16&end=2026-11-20&customer=${customer}`)).json();
 expect(data.tasks.some(task=>task.order_id===id&&task.kind==='domestic_excel'&&task.effective_on==='2026-11-20')).toBeTruthy();
 expect(data.tasks.some(task=>task.order_id===id&&task.kind==='domestic_excel'&&task.effective_on==='2026-11-17')).toBeTruthy();
 // Move it back: two shipment tasks for one PO must still count as one company.
 await update('2026-11-17');await page.screenshot({path:resolve(`../../.runtime/inline-due-list-${info.project.name}.png`),fullPage:true});
 data=await(await page.request.get(`/api/calendar/?start=2026-11-17&end=2026-11-17&customer=${customer}`)).json();
 const group=data.groups.find(group=>group.kind==='domestic_excel');expect(group.customer_count).toBe(1);expect(group.title).toContain('1건');expect(group.tasks.filter(task=>task.order_id===id)).toHaveLength(2);
 expect(data.due_markers).toHaveLength(1);
 await page.goto(`/calendar/?date=2026-11-17&customer=${customer}`);await expect(page.locator('[data-agenda]')).toContainText('1건 (업체 기준)');
 await expect(page.locator('.calendar-day.selected .event').filter({hasText:'· 1건'})).toHaveCount(3);
 await page.screenshot({path:resolve(`../../.runtime/inline-due-calendar-${info.project.name}.png`),fullPage:true});
});

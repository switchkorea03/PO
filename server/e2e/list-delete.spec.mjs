import {test,expect} from '@playwright/test';
import {resolve} from 'node:path';

test('delete is immediately visible on every PO item row, with cancel and restore',async({page},info)=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');
 await page.goto('/orders/new/');await page.locator('[name=customer_id]').selectOption({label:'범진전자'});
 const number=`LIST-DELETE-${info.project.name}-${Date.now()}`;await page.locator('[name=po_number]').fill(number);
 await page.getByRole('button',{name:'＋ 품목 추가',exact:true}).click();
 for(let i=0;i<2;i++){const line=page.locator('.line-row').nth(i);await line.locator('[data-field=name]').fill(`목록삭제 테스트 ${i+1}`);await line.locator('[data-field=quantity]').fill('1000');await line.locator('[data-field=requested_due]').fill('2026-10-29');}
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);const orderUrl=page.url();
 await page.goto('/orders/');const rows=page.getByRole('row').filter({hasText:number});await expect(rows).toHaveCount(2);
 for(let i=0;i<2;i++){
  const button=rows.nth(i).locator('td').first().getByRole('button',{name:'삭제',exact:true});await expect(button).toBeVisible();
  const box=await button.boundingBox();expect(box.x).toBeGreaterThanOrEqual(0);expect(box.x+box.width).toBeLessThanOrEqual(info.project.use.viewport.width);
 }
 page.once('dialog',dialog=>dialog.dismiss());await rows.first().getByRole('button',{name:'삭제',exact:true}).click();await expect(rows).toHaveCount(2);
 await page.screenshot({path:resolve(`../../.runtime/2026-10-27-list-delete-${info.project.name}.png`),fullPage:true});
 const deletion=page.waitForResponse(response=>response.url()===orderUrl+'delete/'&&response.request().method()==='POST');
 page.once('dialog',dialog=>dialog.accept());await rows.nth(1).getByRole('button',{name:'삭제',exact:true}).click();expect((await deletion).status()).toBe(302);await expect(rows).toHaveCount(0);
 await expect(page.getByText('PO를 휴지통으로 이동했습니다.',{exact:true})).toBeVisible();
 await page.goto('/orders/?state=deleted');const trash=page.getByRole('row').filter({hasText:number});await expect(trash).toHaveCount(2);await trash.first().getByRole('button',{name:'복원',exact:true}).click();await expect(page).toHaveURL(orderUrl);
 await page.goto('/orders/');await expect(rows).toHaveCount(2);
});

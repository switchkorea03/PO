import {test,expect} from '@playwright/test';
test('persistent PO split shipment and calendar workflow',async({page},info)=>{
 const saveAndReload=async action=>{await Promise.all([page.waitForEvent('framenavigated',frame=>frame===page.mainFrame()),action()]);await page.waitForLoadState('networkidle');};
 await page.goto('/accounts/login/');
 await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();
 await page.goto('/orders/new/');await page.getByLabel('새 고객명').fill('고객-'+info.project.name);await page.getByRole('button',{name:'고객 추가',exact:true}).click();await expect(page.locator('[name=customer_id]')).not.toHaveValue('');
 await page.getByLabel('PO 번호',{exact:true}).fill('PO-'+info.project.name);
 await page.locator('[data-field="code"]').first().fill('ITEM-1');await page.locator('[data-field="name"]').first().fill('테스트 부품');await page.locator('[data-field="quantity"]').first().fill('100');await page.locator('[data-field="requested_due"]').first().fill('2026-10-19');
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);
 const orderUrl=page.url();await expect(page.getByTestId('remaining').first()).toContainText('100');
 const first=page.locator('[data-shipment-form]').first();await first.locator('[data-allocation]').first().fill('70');await saveAndReload(()=>first.getByRole('button',{name:'회차 저장',exact:true}).click());
 const add=page.locator('[data-shipment-form][data-new="true"]');await add.locator('[name="ship_on"]').fill('2026-10-20');await add.locator('[data-allocation]').first().fill('30');await saveAndReload(()=>add.getByRole('button',{name:'회차 추가',exact:true}).click());
 await saveAndReload(()=>page.locator('[data-confirm-shipment]').first().click());await expect(page.getByTestId('remaining').first()).toContainText('30');
 await page.reload();await expect(page.getByTestId('remaining').first()).toContainText('30');
 await page.goto('/calendar/?date=2026-10-16');await expect(page.locator('main')).toContainText('출고 내역 공유');
 await page.locator('[data-agenda] a').filter({hasText:'출고 내역 공유'}).filter({hasText:'고객-'+info.project.name}).first().click();await page.waitForLoadState('networkidle');await saveAndReload(()=>page.locator('[data-substep]').first().check());await expect(page.locator('[data-task-state]')).toContainText('완료');
 await page.goto(orderUrl);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

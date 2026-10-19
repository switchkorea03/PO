import {test,expect} from '@playwright/test';
test('repeated customer add keeps a single selectable customer',async({page},info)=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();
 await page.goto('/orders/new/');await page.getByLabel('새 고객명').fill('중복확인-'+info.project.name);
 for(let i=0;i<5;i++){
  await page.getByRole('button',{name:'고객 추가',exact:true}).click();
  await expect(page.locator('[name=customer_id] option').filter({hasText:'중복확인-'+info.project.name})).toHaveCount(1);
  await expect(page.getByRole('button',{name:'고객 추가',exact:true})).toBeEnabled();
 }
 await page.reload();await expect(page.locator('[name=customer_id] option').filter({hasText:'중복확인-'+info.project.name})).toHaveCount(1);
});

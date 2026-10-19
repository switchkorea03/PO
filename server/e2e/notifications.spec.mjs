import {test,expect} from '@playwright/test';
test('personal SMS configuration and fake history are explicit',async({page})=>{
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();
 await page.goto('/settings/notices/');await expect(page.getByText('모의 발송 · 실제 문자 없음',{exact:true})).toBeVisible();
 await page.getByLabel('수신번호',{exact:true}).fill('01012345678');await page.getByLabel('등록된 발신번호',{exact:true}).fill('0212345678');await page.getByLabel('알림 사용',{exact:true}).check();await page.getByRole('button',{name:'설정 저장',exact:true}).click();await page.waitForLoadState('networkidle');
 await expect(page.getByLabel('수신번호',{exact:true})).toHaveValue('01012345678');
 await page.goto('/notices/history/');await expect(page.getByText('모의 공급자입니다. 실제 문자가 발송되지 않습니다.',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

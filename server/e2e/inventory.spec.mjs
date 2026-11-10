import {test,expect} from '@playwright/test';

test('inventory navigation, unknown stock, search and desktop preparation are usable',async({page},info)=>{
 await page.goto('/inventory/');await expect(page).toHaveURL(/accounts\/login/);
 await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();
 await expect(page).toHaveURL(/\/inventory\/$/);
 await expect(page.getByRole('navigation',{name:'주 메뉴'}).getByRole('link',{name:'재고 확인',exact:true})).toHaveAttribute('aria-current','page');
 await expect(page.getByRole('heading',{name:'재고 확인',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'ERP 재고 새로고침'})).toBeDisabled();
 await expect(page.getByLabel('ERP 연결 상태')).toContainText('ERP 미연결');
 await expect(page.locator('.inventory-table')).toContainText('JTP1135JEM');await expect(page.locator('.stock-unknown').first()).toHaveText('—');
 await page.getByLabel('재고 품목 검색').fill('JTP1135JEM');await page.getByRole('button',{name:'검색',exact:true}).click();await expect(page.locator('.inventory-table tbody tr')).toHaveCount(1);
 await expect(page.locator('.inventory-table tbody tr')).toContainText('JTP1135JEM');
 await page.getByLabel('재고 품목 검색').fill('NO-SUCH-ITEM');await page.getByRole('button',{name:'검색',exact:true}).click();await expect(page.locator('.inventory-table')).toContainText('검색한 품목이 없습니다');
 await page.getByRole('link',{name:'초기화',exact:true}).click();await page.getByText('데스크탑에서 ERP 연결하기',{exact:true}).click();await expect(page.locator('.inventory-guide')).toContainText('GitHub');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await page.screenshot({path:`../../.runtime/inventory-${info.project.name}.png`,fullPage:true});
});

import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

test('all company work is visible in calendar without a popup or more button',async({page},info)=>{
 const names=['범진전자','SJI','솔루엠'].map(name=>`${name}-${info.project.name}`);
 const script=`import os,sys,json
sys.path.insert(0,sys.argv[1]);os.environ['DJANGO_SETTINGS_MODULE']='config.e2e_settings'
import django;django.setup()
from django.conf import settings
assert settings.DATABASES['default']['NAME']=='po_calendar_e2e'
from orders.tests.factories import make_order
from work.models import Task
from datetime import date
orders=[]
for name in json.loads(sys.argv[2]):
 order=make_order(dues=('2026-11-17',));order.customer.name=name;order.customer.save();orders.append(order)
for index,(company,kind,state) in enumerate([(0,'domestic_excel','open'),(0,'domestic_request','open'),(0,'domestic_share','done'),(1,'domestic_excel','open'),(1,'domestic_request','partial'),(2,'domestic_excel','open')]):
 Task.objects.create(order=orders[company],scope_key=str(orders[company].id)+str(index),kind=kind,title={'domestic_excel':'출고 준비','domestic_request':'출고 요청','domestic_share':'출고 내역 공유'}[kind],state=state,effective_on=date(2026,11,17))
`;
 execFileSync(resolve('../../.venv/Scripts/python.exe'),['-c',script,resolve('..'),JSON.stringify(names)]);
 await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');

 await page.goto('/calendar/?date=2026-11-17');
 await expect(page.locator('aside.agenda')).toHaveCount(0);await expect(page.locator('dialog')).toHaveCount(0);await expect(page.locator('.day-more')).toHaveCount(0);
 const cell=page.locator('[data-calendar-date="2026-11-17"]');
 await expect(cell).not.toContainText('미완료');await expect(cell).not.toContainText('예정');
 for(const name of names)await expect(cell.getByRole('heading',{name,exact:true})).toBeVisible();
 expect(await cell.locator('.calendar-work').count()).toBeGreaterThanOrEqual(9);
 await expect(cell).toContainText('출고 준비');await expect(cell).toContainText('출고 요청');await expect(cell).toContainText('출고 내역 공유');await expect(cell).toContainText('납기일');
 expect(await cell.evaluate(element=>element.scrollHeight<=element.clientHeight+1)).toBeTruthy();
 await page.screenshot({path:resolve(`../../.runtime/calendar-all-visible-${info.project.name}.png`),fullPage:true});
 await page.getByRole('link',{name:'주간',exact:true}).click();await expect(page.locator('.week-mode')).toBeVisible();
 const option=await page.locator('select[name=customer] option').filter({hasText:names[0]}).getAttribute('value');await page.locator('select[name=customer]').selectOption(option);await page.getByRole('button',{name:'적용',exact:true}).click();
 await expect(page.locator('[data-calendar-date="2026-11-17"] .calendar-company')).toHaveCount(1);
 await expect(page.locator('[data-calendar-date="2026-11-17"]')).toContainText(names[0]);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 const taskLink=page.locator('[data-calendar-date="2026-11-17"] .calendar-po-links a[href^="/tasks/"]').first();await taskLink.click();await expect(page).toHaveURL(/\/tasks\/[0-9a-f-]+\/$/);
});

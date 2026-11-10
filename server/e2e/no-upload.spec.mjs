import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

const snapshot=number=>JSON.parse(execFileSync(resolve('../../.venv/Scripts/python.exe'),[resolve('db_snapshot.py'),number],{encoding:'utf8'}));
async function record(info,label,data){await info.attach(label,{body:Buffer.from(JSON.stringify(data,null,2)),contentType:'application/json'});}
async function save(page,action){await Promise.all([page.waitForEvent('framenavigated',frame=>frame===page.mainFrame()),action()]);await page.waitForLoadState('networkidle');}
async function login(page){await page.goto('/accounts/login/');await page.getByLabel('사용자 이름').fill('e2e-manager');await page.getByLabel('비밀번호').fill('local-e2e-password');await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL('**/calendar/');}
async function create(page,info,type){
 const number=`NOFILE-${type}-${info.project.name}-${Date.now()}`;
 await page.goto('/orders/new/');await page.getByLabel('새 고객명').fill(`가상연동검증-${type}-${info.project.name}`);
 await page.locator('#customer-type').selectOption(type);await page.locator('#customer-currency').fill(type==='overseas'?'USD':'KRW');
 await page.getByRole('button',{name:'고객 추가',exact:true}).click();await expect(page.locator('[name=customer_id]')).not.toHaveValue('');
 await page.getByLabel('PO 번호',{exact:true}).fill(number);await expect(page.locator('[name=received_on]')).toBeHidden();
 await page.locator('[data-field=code]').first().fill('VIRTUAL-001');await page.locator('[data-field=name]').first().fill('가상 테스트 부품');
 await page.locator('[data-field=quantity]').first().fill('100');await page.locator('[data-field=unit_price]').first().fill(type==='overseas'?'12.5':'1500');
 if(type==='domestic')await page.locator('[data-field=requested_due]').first().fill('2026-10-29');
 await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(/\/orders\/[0-9a-f-]+\/$/);return number;
}

test('no PDF: domestic UI -> API -> PostgreSQL -> calendar and shipment persistence',async({page},info)=>{
 test.setTimeout(90000);const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await login(page);const number=await create(page,info,'domestic');const orderUrl=page.url();
 let db=snapshot(number);expect(db.database).toBe('po_calendar_e2e');expect(db.attached_sources).toBe(0);
 expect(Number(db.lines[0].quantity)).toBe(100);expect(Number(db.lines[0].amount)).toBe(150000);expect(db.tasks).toHaveLength(5);
 expect(db.tasks.find(task=>task.kind==='domestic_share').date).toBe('2026-10-28');await record(info,'domestic-created-db',db);
 const form=page.locator('[data-shipment-form]').first();
 await form.locator('[data-allocation]').fill('101');
 const rejected=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith('/shipments/'));
 await form.getByRole('button',{name:'회차 저장',exact:true}).click();expect((await rejected).status()).toBeGreaterThanOrEqual(400);
 expect(Number(snapshot(number).lines[0].shipped)).toBe(0);await expect(page.locator('#message')).toContainText('초과');
 await form.locator('[data-allocation]').fill('70');await save(page,()=>form.getByRole('button',{name:'회차 저장',exact:true}).click());
 const add=page.locator('[data-shipment-form][data-new=true]');await add.locator('[name=ship_on]').fill('2026-10-30');await add.locator('[data-allocation]').fill('30');await save(page,()=>add.getByRole('button',{name:'회차 추가',exact:true}).click());
 await save(page,()=>page.locator('[data-confirm-shipment]').first().click());
 await page.reload();await expect(page.getByTestId('remaining').first()).toContainText('30');
 db=snapshot(number);expect(Number(db.lines[0].shipped)).toBe(70);expect(Number(db.lines[0].remaining)).toBe(30);expect(db.shipments).toHaveLength(2);expect(db.shipments[0].completed).toBe(true);
 await page.goto('/calendar/?date=2026-10-28');await page.locator('[data-agenda] a').filter({hasText:'출고 내역 공유'}).filter({hasText:db.customer}).first().click();
 await save(page,()=>page.locator('[data-substep]').first().check());await page.reload();await expect(page.locator('[data-task-state]')).toContainText('완료');
 db=snapshot(number);expect(db.tasks.some(task=>task.kind==='domestic_share'&&task.state==='done'&&task.done_steps===1)).toBe(true);expect(db.audit).toContain('check_substep');expect(db.audit).toContain('confirm_shipment');await record(info,'domestic-final-db',db);
 await page.goto(orderUrl);await page.screenshot({path:resolve(`../../.runtime/no-upload-domestic-${info.project.name}.png`),fullPage:true});expect(errors).toEqual([]);
});

test('no PDF: overseas dates and edited values persist through real backend and PostgreSQL',async({page},info)=>{
 test.setTimeout(90000);const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await login(page);const number=await create(page,info,'overseas');const orderUrl=page.url();
 let db=snapshot(number);expect(db.type).toBe('overseas');expect(db.attached_sources).toBe(0);expect(Number(db.lines[0].amount)).toBe(1250);
 const received=db.received_on;const nextTuesday=new Date(received+'T12:00:00Z');nextTuesday.setUTCDate(nextTuesday.getUTCDate()+9-(nextTuesday.getUTCDay()||7));
 expect(received).toBe(new Date(Date.now()+9*60*60*1000).toISOString().slice(0,10));
 expect(db.tasks.find(task=>task.kind==='overseas_invoice').date).toBe(received);expect(db.tasks.find(task=>task.kind==='overseas_bl_eta').date).toBe(nextTuesday.toISOString().slice(0,10));
 expect(db.tasks.filter(task=>task.suspended)).toHaveLength(3);await record(info,'overseas-created-db',db);
 const form=page.locator('[data-shipment-form]').first();await form.locator('[name=etd]').fill('2026-10-31');await form.locator('[name=eta]').fill('2026-11-04');await save(page,()=>form.getByRole('button',{name:'회차 저장',exact:true}).click());
 await page.reload();await expect(page.locator('[data-shipment-form]').first().locator('[name=etd]')).toHaveValue('2026-10-31');
 db=snapshot(number);expect(db.shipments[0].eta).toBe('2026-11-04');for(const kind of ['overseas_erp','overseas_mail','overseas_excel']){expect(db.tasks.find(task=>task.kind===kind).date).toBe('2026-11-02');expect(db.tasks.find(task=>task.kind===kind).suspended).toBe(false);}
 await page.getByRole('link',{name:'PO 정보 수정',exact:true}).click();await expect(page.locator('[name=received_on]')).toBeHidden();await page.locator('[data-field=unit_price]').fill('13.5');await page.getByRole('button',{name:'PO 저장',exact:true}).click();await expect(page).toHaveURL(orderUrl);
 db=snapshot(number);expect(db.received_on).toBe(received);expect(Number(db.lines[0].amount)).toBe(1350);expect(db.tasks.find(task=>task.kind==='overseas_bl_eta').date).toBe(nextTuesday.toISOString().slice(0,10));
 await page.goto('/calendar/?date=2026-11-02');await expect(page.locator('[data-agenda]')).toContainText(db.customer);await record(info,'overseas-final-db',db);
 await page.goto(orderUrl);await page.screenshot({path:resolve(`../../.runtime/no-upload-overseas-${info.project.name}.png`),fullPage:true});expect(errors).toEqual([]);
});

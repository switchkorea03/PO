from datetime import date
from django.test import SimpleTestCase,TestCase
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order
from work.models import Task
from work.calendar_presentation import day_summary


class CalendarPresentationTests(SimpleTestCase):
    def task(self,id,customer,state='open',suspended=False):
        return {'id':id,'customer_id':customer,'customer_name':f'업체{customer}',
                'kind':'domestic_excel','title':'출고 준비','state':state,'suspended':suspended}

    def test_crowded_day_shows_every_company_without_preview_limit(self):
        tasks=[self.task(i,i) for i in range(5)]
        data=day_summary(tasks,[],date(2026,11,17),date(2026,11,18))
        self.assertEqual(data['customer_count'],5)
        self.assertEqual(data['pending_count'],5)
        self.assertEqual(len(data['company_blocks']),5)
        self.assertTrue(all(item['status']=='지연' for group in data['company_blocks'] for item in group['items']))

    def test_multiple_tasks_for_one_company_and_completed_states(self):
        tasks=[self.task(1,1),self.task(2,1,'done'),self.task(3,2,'cancelled'),self.task(4,3,suspended=True)]
        data=day_summary(tasks,[],date(2026,11,17),date(2026,11,17))
        self.assertEqual(data['customer_count'],2)
        self.assertEqual(data['pending_count'],1)
        self.assertEqual(data['company_blocks'][0]['name'],'업체1')
        self.assertEqual(data['company_blocks'][0]['items'][0]['status'],'부분완료')

    def test_due_only_day_is_visible_without_inventing_pending_tasks(self):
        due={'title':'범진전자(납기)','customer_id':'c1','customer_name':'범진전자','url':'/orders/1/'}
        data=day_summary([], [due],date(2026,11,17),date(2026,11,17))
        self.assertEqual(data['customer_count'],1)
        self.assertEqual(data['pending_count'],0)
        self.assertEqual(data['company_blocks'][0]['items'][0]['status'],'납기')


class CalendarAgendaTests(TestCase):
    def test_company_agenda_is_complete_and_filterable_on_crowded_day(self):
        user=get_user_model().objects.create_user('calendar-reader');self.client.force_login(user)
        orders=[make_order(dues=('2026-11-17',)) for _ in range(3)]
        for index in range(8):
            Task.objects.create(order=orders[index%3],scope_key=f'calendar:{index}',kind='domestic_excel',title='출고 준비',effective_on=date(2026,11,17))
        Task.objects.create(order=orders[0],scope_key='calendar:cancelled',kind='domestic_excel',title='취소된 출고 준비',state='cancelled',effective_on=date(2026,11,17))
        response=self.client.get('/calendar/?date=2026-11-17')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['selected_summary']['customer_count'],3)
        self.assertEqual(response.context['selected_summary']['pending_count'],8)
        self.assertEqual(sum(len(group['tasks']) for group in response.context['agenda_groups']),8)
        self.assertNotContains(response,'나머지')
        self.assertNotContains(response,'<dialog')
        self.assertNotContains(response,'#day-agenda')
        day=next(day for week in response.context['weeks'] for day in week if day['date']==date(2026,11,17))
        self.assertEqual(len(day['company_blocks']),3)
        self.assertEqual(sum(len(item['links']) for group in day['company_blocks'] for item in group['items']),11)
        filtered=self.client.get(f'/calendar/?date=2026-11-17&customer={orders[0].customer_id}')
        self.assertEqual(len(filtered.context['agenda_groups']),1)
        self.assertEqual(filtered.context['selected_summary']['pending_count'],3)

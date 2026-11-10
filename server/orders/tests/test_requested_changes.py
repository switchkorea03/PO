from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.test import TestCase, SimpleTestCase
from orders.models import Customer, Order
from orders.forms import order_input
from orders.services import save_order
from work.services import reconcile_order
from work.queries import get_notice_candidates
from .factories import make_order, make_shipment


class RequestedChangesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('requested-changes')
        self.client.force_login(self.user)

    def test_reference_image_item_codes_autofill_all_four_internal_names(self):
        pairs=[('MESA100005A','JT1138BEM'),('MESA100007A','JT1140WJ-BEM'),
               ('MESA100008A','JTP1169BEM'),('MESAH00002A','JT1280A6')]
        customer=Customer.objects.create(name='이미지 품목매핑')
        data=order_input({'customer_id':str(customer.id),'po_number':'IMAGE-MAPPING',
            'order_type':'domestic','lines':[{'code':code,'name':code,
                'quantity':'1000','unit':'EA','requested_due':'2026-10-29'} for code,_ in pairs]})
        order=save_order(data,self.user.id,None)
        for code,internal in pairs:
            self.assertEqual(order.lines.get(code=code).internal_name,internal)
        response=self.client.get('/orders/new/')
        for code,internal in pairs:
            self.assertContains(response,code)
            self.assertContains(response,internal)

    def test_known_customer_item_gets_internal_name_and_list_columns(self):
        customer = Customer.objects.create(name='품목연결검증')
        data = order_input({'customer_id':str(customer.id),'po_number':'MAPPING-001',
            'order_type':'domestic','lines':[{'code':'MESA100005A','name':'MESA100005A',
            'quantity':'12000','unit':'EA','unit_price':'1500','requested_due':'2026-10-29'}]})
        order = save_order(data,self.user.id,None)
        line = order.lines.get()
        self.assertEqual(line.internal_name,'JT1138BEM')
        response = self.client.get('/orders/')
        self.assertContains(response,'MESA100005A')
        self.assertContains(response,'JT1138BEM')
        self.assertContains(response,'12,000')
        self.assertContains(response,'18,000,000')
        for label in ['발주서 등록일','PO 번호','품목명','수량','단가','공급가액','납기일']:
            self.assertContains(response,label)

    def test_explicit_internal_name_overrides_mapping_and_is_editable(self):
        customer = Customer.objects.create(name='수동품목연결')
        data = order_input({'customer_id':str(customer.id),'po_number':'MAPPING-002',
            'order_type':'domestic','lines':[{'code':'MESA100007A','name':'MESA100007A',
            'internal_name':'CUSTOM-PART','quantity':'1000','unit':'EA','requested_due':'2026-10-29'}]})
        order = save_order(data,self.user.id,None)
        self.assertEqual(order.lines.get().internal_name,'CUSTOM-PART')
        self.assertContains(self.client.get(f'/orders/{order.id}/edit/'),'CUSTOM-PART')

    def test_delete_hides_po_calendar_and_notice_without_destroying_history_then_restore(self):
        order = make_order()
        make_shipment(order,'100',ship_on='2026-10-29')
        reconcile_order(order.id,self.user.id)
        order.refresh_from_db()
        tasks = list(order.tasks.values_list('id',flat=True))
        response = self.client.post(f'/orders/{order.id}/delete/',{'row_version':order.row_version},content_type='application/json')
        self.assertEqual(response.status_code,200)
        order.refresh_from_db()
        self.assertTrue(order.is_deleted)
        self.assertEqual(order.tasks.count(),len(tasks))
        self.assertTrue(order.history.filter(action='delete_order').exists())
        self.assertNotContains(self.client.get('/orders/'),order.po_number)
        self.assertEqual(self.client.get(f'/orders/{order.id}/').status_code,404)
        payload = self.client.get('/api/calendar/?start=2026-10-01&end=2026-11-30').json()
        self.assertFalse(any(str(item['order_id'])==str(order.id) for item in payload['tasks']))
        self.assertFalse(any(str(item['order_id'])==str(order.id) for item in payload['due_markers']))
        self.assertFalse(any(item.id in tasks for item in get_notice_candidates(date(2026,11,1),True)))
        self.assertContains(self.client.get('/orders/?state=deleted'),order.po_number)
        restored = self.client.post(f'/orders/{order.id}/restore/',{'row_version':order.row_version},content_type='application/json')
        self.assertEqual(restored.status_code,200)
        self.assertContains(self.client.get('/orders/'),order.po_number)

    def test_deleted_po_rejects_stale_edit(self):
        order = make_order()
        self.client.post(f'/orders/{order.id}/delete/',{'row_version':order.row_version},content_type='application/json')
        self.assertEqual(self.client.get(f'/orders/{order.id}/edit/').status_code,404)

    def test_list_delete_form_redirects_with_visible_result(self):
        order = make_order()
        response = self.client.post(f'/orders/{order.id}/delete/',
            {'row_version':order.row_version},follow=True)
        self.assertRedirects(response,'/orders/')
        self.assertContains(response,'PO를 휴지통으로 이동했습니다.')
        self.assertNotContains(response,order.po_number)
        order.refresh_from_db()
        self.assertTrue(order.is_deleted)

    def test_list_delete_stale_form_shows_error_without_deleting(self):
        order = make_order()
        response = self.client.post(f'/orders/{order.id}/delete/',
            {'row_version':order.row_version-1},follow=True)
        self.assertRedirects(response,'/orders/')
        self.assertContains(response,'다른 사용자가 수정했습니다.')
        order.refresh_from_db()
        self.assertFalse(order.is_deleted)

    def test_requested_customer_groups_are_seeded(self):
        for name in ['범진전자','SJI','SJIT']:
            self.assertEqual(Customer.objects.get(name=name).default_type,'domestic')
        for name in ['켐트로비나','솔루엠','리모트솔루션']:
            self.assertEqual(Customer.objects.get(name=name).default_type,'overseas')

    def test_revision_keeps_existing_internal_name(self):
        from intake.models import SourceFile,ExtractionJob,ExtractionDraft
        order=make_order();line=order.lines.get();line.internal_name='CUSTOM-PART';line.save()
        source=SourceFile.objects.create(sha256='b'*64,path='unused.png',original_name='revision.png',extension='.png',size=1,uploaded_by=self.user)
        job=ExtractionJob.objects.create(source=source,status='done')
        draft=ExtractionDraft.objects.create(job=job,result={'fields':{},'lines':[{'code':{'value':line.code},'name':{'value':line.name}}]})
        response=self.client.get(f'/intake/{draft.id}/review/?target={order.id}')
        self.assertEqual(response.context['initial_data']['lines'][0]['internal_name'],'CUSTOM-PART')


class NumberDisplayTests(SimpleTestCase):
    def test_thousands_grouping_preserves_decimal_precision(self):
        template = Template('{% load po_numbers %}{{ value|po_number }}')
        for value,expected in [(Decimal('12345.6700000000'),'12,345.67'),
                               (Decimal('0'),'0'),(Decimal('12345678901234567890.1234567890'),'12,345,678,901,234,567,890.123456789')]:
            self.assertEqual(template.render(Context({'value':value})),expected)

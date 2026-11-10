from django.test import SimpleTestCase,TestCase
from django.contrib.auth import get_user_model
from orders.item_mapping import mapped_internal_name
from orders.models import Customer
from orders.forms import order_input
from orders.services import save_order


NAMES=('JT1140WJ-BEM','JES1612GWAS','JS1267EM','JTP1135JEM','JT1126EM','JT1127WEM',
       'JS6901EM','JT1136SHAEM','JT-S1102PEM','JT1152EM','JT1138FEM')


class SpecNameMatchingTests(SimpleTestCase):
    def test_all_reference_names_are_recognized_inside_specs(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual(mapped_internal_name('CUSTOMER-001',f'SWITCH;{name};TACT;5*5'),name)

    def test_exact_model_boundaries_and_ambiguous_specs(self):
        for spec in ('XJT1126EM','JT1126EM-X','JT1126EM2','JT1126EM / JS1267EM'):
            self.assertEqual(mapped_internal_name('UNKNOWN',spec),'')
        self.assertEqual(mapped_internal_name('UNKNOWN','switch; jt1140wj– bem; tact'),'JT1140WJ-BEM')
        self.assertEqual(mapped_internal_name('MESA100005A','SPEC;JT1138FEM;TACT'),'JT1138FEM')

    def test_additional_spec_aliases_and_existing_full_model(self):
        self.assertEqual(mapped_internal_name('UNKNOWN','SWITCH;SKRWAEE030;TACT'),'JTP1135JEM')
        self.assertEqual(mapped_internal_name('UNKNOWN','JS6901; Slide Switch'),'JS6901')
        self.assertEqual(mapped_internal_name('UNKNOWN','SWITCH;JS6901EM;TACT'),'JS6901EM')
        self.assertEqual(mapped_internal_name('UNKNOWN','SKRWAEE030 / JTP1135JEM'),'JTP1135JEM')


class SpecNamePersistenceTests(TestCase):
    def test_autofill_is_saved_and_explicit_manual_name_is_kept(self):
        user=get_user_model().objects.create_user('spec-manager')
        customer=Customer.objects.create(name='스펙자동연결')
        data=order_input({'customer_id':str(customer.id),'po_number':'SPEC-AUTO','order_type':'domestic',
            'lines':[{'code':'C1','name':'SWITCH;JES1612GWAS;PUSH','quantity':'100','unit':'EA','requested_due':'2026-11-17'},
                     {'code':'C2','name':'SWITCH;JS1267EM;SLIDE','internal_name':'MANUAL-PART','quantity':'100','unit':'EA','requested_due':'2026-11-17'}]})
        order=save_order(data,user.id,None)
        self.assertEqual(order.lines.get(code='C1').internal_name,'JES1612GWAS')
        self.assertEqual(order.lines.get(code='C2').internal_name,'MANUAL-PART')

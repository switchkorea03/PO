from io import BytesIO
from pathlib import Path
import tempfile
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import load_workbook
from orders.services import cancel_order,delete_order,confirm_shipment
from intake.services import upload_source
from intake.models import OrderSource,ExtractionDraft
from intake.tests.test_upload import excel_bytes
from .factories import make_order,make_shipment


class CancelledReregistrationTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('reregister-manager')
        self.client.force_login(self.user)
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        override=override_settings(PRIVATE_MEDIA_ROOT=Path(temporary.name))
        override.enable();self.addCleanup(override.disable)

    def cancelled_order(self,deleted=False,shipped=False):
        content=excel_bytes();uploaded=upload_source(SimpleUploadedFile('po.xlsx',content),self.user.id)
        order=make_order(dues=('2026-10-29',))
        if shipped:
            completed=make_shipment(order,'30',ship_on='2026-10-29')
            confirm_shipment(completed.id,self.user.id,completed.row_version)
        pending=make_shipment(order,'70' if shipped else '100',ship_on='2026-10-29')
        OrderSource.objects.create(order=order,source_id=uploaded.source_id,version=1,confirmed_by=self.user)
        order.refresh_from_db();cancel_order(order.id,self.user.id,order.row_version)
        if deleted:
            order.refresh_from_db();delete_order(order.id,self.user.id,order.row_version)
        return order,pending,content

    def reupload(self,content):
        return self.client.post('/intake/upload/',{'file':SimpleUploadedFile('again.xlsx',content)},follow=True)

    def save_review(self,order,response):
        data=response.context['initial_data'];data['note']='재등록 확인'
        return self.client.post(f'/orders/{order.id}/reregister/',data,content_type='application/json')

    def assert_reregistration(self,deleted):
        order,pending,content=self.cancelled_order(deleted=deleted)
        response=self.reupload(content)
        self.assertRedirects(response,f'/orders/{order.id}/reregister/')
        order.refresh_from_db();self.assertTrue(order.cancelled)
        self.assertEqual(order.is_deleted,deleted)
        saved=self.save_review(order,response);self.assertEqual(saved.status_code,200)
        order.refresh_from_db();self.assertFalse(order.cancelled);self.assertFalse(order.is_deleted)
        pending.refresh_from_db();self.assertTrue(pending.cancelled)
        new=order.shipments.get(cancelled=False,completed=False)
        self.assertEqual(new.allocations.get().quantity,100)
        self.assertTrue(order.tasks.filter(shipment=new,state='open').exists())
        self.assertEqual(order.source_versions.count(),1)
        self.assertTrue(order.history.filter(action='cancel_order').exists())
        self.assertTrue(order.history.filter(action='reregister_order').exists())

    def test_cancelled_po_can_be_reuploaded_and_saved(self):
        self.assert_reregistration(deleted=False)

    def test_cancelled_po_in_trash_can_be_reuploaded_and_saved(self):
        self.assert_reregistration(deleted=True)

    def test_invalid_save_rolls_back_reactivation(self):
        order,pending,content=self.cancelled_order(deleted=True)
        response=self.reupload(content);self.assertEqual(response.status_code,200)
        data=response.context['initial_data'];data['lines'][0]['quantity']='0'
        saved=self.client.post(f'/orders/{order.id}/reregister/',data,content_type='application/json')
        self.assertEqual(saved.status_code,422)
        order.refresh_from_db();self.assertTrue(order.is_deleted);self.assertTrue(order.cancelled)
        self.assertEqual(order.shipments.count(),1)
        self.assertFalse(order.history.filter(action='reregister_order').exists())

    def test_reregistration_preserves_completed_shipments(self):
        order,pending,content=self.cancelled_order(shipped=True)
        response=self.reupload(content);saved=self.save_review(order,response)
        self.assertEqual(saved.status_code,200)
        self.assertEqual(order.shipments.get(completed=True).allocations.get().quantity,30)
        self.assertEqual(order.shipments.get(cancelled=False,completed=False).allocations.get().quantity,70)
        self.assertEqual(order.lines.get().shipped,30)

    def test_new_source_for_cancelled_trashed_po_can_be_confirmed(self):
        order,pending,content=self.cancelled_order(deleted=True)
        workbook=load_workbook(BytesIO(content));workbook.active.append(['비고','새 원본'])
        output=BytesIO();workbook.save(output);workbook.close()
        uploaded=upload_source(SimpleUploadedFile('revision.xlsx',output.getvalue()),self.user.id)
        line=order.lines.get()
        draft=ExtractionDraft.objects.create(job_id=uploaded.job_id,result={
            'fields':{'customer_name':{'value':order.customer.name},'po_number':{'value':order.po_number}},
            'lines':[{key:{'value':value} for key,value in {'code':line.code,'name':line.name,
                'quantity':'100','unit':'EA','currency':'KRW','requested_due':'2026-10-29'}.items()}]})
        response=self.client.get(f'/intake/{draft.id}/review/')
        self.assertEqual(response.context['initial_data']['target_order_id'],str(order.id))
        saved=self.client.post(f'/intake/{draft.id}/confirm/',response.context['initial_data'],content_type='application/json')
        self.assertEqual(saved.status_code,200)
        order.refresh_from_db();self.assertFalse(order.cancelled);self.assertFalse(order.is_deleted)
        self.assertEqual(order.source_versions.count(),2)

    def test_overseas_order_tasks_reopen_and_keep_completed_steps(self):
        content=excel_bytes();uploaded=upload_source(SimpleUploadedFile('overseas.xlsx',content),self.user.id)
        order=make_order('overseas');make_shipment(order,'100')
        OrderSource.objects.create(order=order,source_id=uploaded.source_id,version=1,confirmed_by=self.user)
        task=order.tasks.get(kind='overseas_invoice')
        from work.services import set_substep
        step=task.substeps.first();set_substep(step.id,True,self.user.id,task.row_version)
        task.refresh_from_db();old_state=task.state
        order.refresh_from_db();cancel_order(order.id,self.user.id,order.row_version)
        response=self.reupload(content);saved=self.save_review(order,response)
        self.assertEqual(saved.status_code,200)
        task.refresh_from_db();step.refresh_from_db()
        self.assertTrue(step.done)
        self.assertEqual(task.state,old_state)
        self.assertNotEqual(order.tasks.get(kind='overseas_bl_eta').state,'cancelled')

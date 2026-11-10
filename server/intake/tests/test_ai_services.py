import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from intake.services import upload_source
from intake.models import ExtractionDraft,GeminiReview,GeminiDailyUsage
from intake.gemini import normalize_proposal,GeminiLimitError
from orders.models import Order
from .test_upload import excel_bytes
from .test_gemini import AI_DOCUMENT


@override_settings(GEMINI_API_KEY='test-server-key',GEMINI_MODEL='gemini-3.1-flash-lite',GEMINI_DAILY_LIMIT=2)
class GeminiWorkflowTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('ai-manager');self.client.force_login(self.user)
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        override=override_settings(PRIVATE_MEDIA_ROOT=Path(temporary.name));override.enable();self.addCleanup(override.disable)
        upload=upload_source(SimpleUploadedFile('po.xlsx',excel_bytes()),self.user.id)
        self.original={'fields':{'po_number':{'value':'LOCAL-001'}},'lines':[],'warnings':[],'evidence':[]}
        self.draft=ExtractionDraft.objects.create(job_id=upload.job_id,result=self.original)

    def analyze(self,**changes):
        return self.client.post(f'/intake/{self.draft.id}/gemini/',{'draft_version':self.draft.row_version,'consent':True,**changes},content_type='application/json')

    @patch('intake.ai_services.analyze_source')
    def test_consent_and_login_are_required_before_any_external_call(self,provider):
        self.assertEqual(self.analyze(consent=False).status_code,422);provider.assert_not_called()
        self.client.logout();self.assertEqual(self.analyze().status_code,302);provider.assert_not_called()

    @patch('intake.ai_services.analyze_source')
    def test_proposal_requires_explicit_apply_and_never_registers_po(self,provider):
        provider.return_value={'result':normalize_proposal(AI_DOCUMENT,self.original),'usage':{'input':20,'output':30,'total':50}}
        response=self.analyze();self.assertEqual(response.status_code,200)
        self.draft.refresh_from_db();self.assertEqual(self.draft.result,self.original);self.assertEqual(Order.objects.count(),0)
        review=GeminiReview.objects.get(pk=response.json()['review_id'])
        self.assertEqual(review.original_result,self.original)
        applied=self.client.post(f'/intake/{self.draft.id}/gemini/{review.id}/apply/',{'draft_version':self.draft.row_version},content_type='application/json')
        self.assertEqual(applied.status_code,200)
        self.draft.refresh_from_db();self.assertEqual(self.draft.result['fields']['po_number']['value'],'AI-001')
        self.assertEqual(self.draft.row_version,2);self.assertIsNone(self.draft.confirmed_order_id);self.assertEqual(Order.objects.count(),0)
        self.assertNotContains(self.client.get(f'/intake/{self.draft.id}/review/'),'test-server-key')

    @patch('intake.ai_services.analyze_source')
    def test_stale_analysis_or_apply_is_rejected(self,provider):
        self.assertEqual(self.analyze(draft_version=99).status_code,409);provider.assert_not_called()
        provider.return_value={'result':normalize_proposal(AI_DOCUMENT,self.original),'usage':{}}
        response=self.analyze();review=GeminiReview.objects.get(pk=response.json()['review_id'])
        self.draft.row_version+=1;self.draft.save()
        applied=self.client.post(f'/intake/{self.draft.id}/gemini/{review.id}/apply/',{'draft_version':1},content_type='application/json')
        self.assertEqual(applied.status_code,409);self.draft.refresh_from_db();self.assertEqual(self.draft.result,self.original)

    def test_fields_outside_ai_scope_are_preserved_without_mutating_local_result(self):
        self.original['fields']['received_on']={'value':'2026-10-01','evidence':[{'page':1}]}
        result=normalize_proposal(AI_DOCUMENT,self.original)
        self.assertEqual(result['fields']['received_on'],self.original['fields']['received_on'])
        result['fields']['received_on']['value']='2026-11-01'
        self.assertEqual(self.original['fields']['received_on']['value'],'2026-10-01')

    @patch('intake.ai_services.analyze_source')
    def test_provider_failure_preserves_draft_and_does_not_retry(self,provider):
        provider.side_effect=GeminiLimitError('Gemini 사용 한도 초과')
        response=self.analyze();self.assertEqual(response.status_code,429);self.assertEqual(provider.call_count,1)
        self.draft.refresh_from_db();self.assertEqual(self.draft.result,self.original)
        self.assertEqual(GeminiReview.objects.get().status,'failed')

    @patch('intake.ai_services.analyze_source')
    def test_daily_app_limit_is_enforced_before_provider_call(self,provider):
        provider.return_value={'result':normalize_proposal(AI_DOCUMENT,self.original),'usage':{}}
        self.assertEqual(self.analyze().status_code,200);self.assertEqual(self.analyze().status_code,200)
        self.assertEqual(self.analyze().status_code,429);self.assertEqual(provider.call_count,2)
        self.assertEqual(GeminiDailyUsage.objects.get().calls,2)

    @patch('intake.ai_services.analyze_source')
    def test_running_duplicate_request_does_not_consume_another_attempt(self,provider):
        GeminiReview.objects.create(draft=self.draft,requested_by=self.user,model='test',draft_version=1,status='running',original_result=self.original)
        self.assertEqual(self.analyze().status_code,409);provider.assert_not_called()

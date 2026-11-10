import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch
from urllib.error import HTTPError
from django.test import SimpleTestCase,override_settings
from common.errors import ValidationError
from intake.gemini import analyze_source,normalize_proposal


AI_DOCUMENT={'po_number':'AI-001','customer_name':'켐트로비나','order_type':'overseas',
 'ordered_on':'2026-11-03','contact':None,'total_amount':'200.00','warnings':[],
 'lines':[{'code':'C-001','name':'PUSH;JES1612GWAS;A','quantity':'1,000','unit':'EA',
  'unit_price':'0.2','currency':'USD','source_amount':'200.00','requested_due':'2026-12-01'}]}


class GeminiNormalizationTests(SimpleTestCase):
    def test_structured_result_has_precise_values_and_known_internal_name(self):
        result=normalize_proposal(AI_DOCUMENT,{})
        self.assertEqual(result['fields']['po_number']['value'],'AI-001')
        self.assertEqual(result['lines'][0]['quantity']['value'],'1000')
        self.assertEqual(result['lines'][0]['internal_name']['value'],'JES1612GWAS')
        self.assertTrue(result['lines'][0]['quantity']['needs_review'])

    def test_unknown_values_are_not_guessed_and_differences_are_flagged(self):
        document=json.loads(json.dumps(AI_DOCUMENT));document['lines'][0]['quantity']=None
        result=normalize_proposal(document,{'fields':{'po_number':{'value':'LOCAL-001'}},'lines':[]})
        self.assertIsNone(result['lines'][0]['quantity']['value'])
        self.assertTrue(any('PO번호' in warning for warning in result['warnings']))

    def test_malformed_numeric_data_and_non_document_response_are_rejected(self):
        for payload in [[],{'lines':'not a list'},{**AI_DOCUMENT,'lines':[{**AI_DOCUMENT['lines'][0],'quantity':'NaN'}]}]:
            with self.assertRaises(ValidationError):normalize_proposal(payload,{})


@override_settings(GEMINI_API_KEY='server-only-test-key',GEMINI_MODEL='gemini-3.1-flash-lite',GEMINI_MAX_FILE_BYTES=10485760)
class GeminiClientTests(SimpleTestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);override=override_settings(PRIVATE_MEDIA_ROOT=self.root)
        override.enable();self.addCleanup(override.disable)
        path=self.root/'synthetic.pdf';path.write_bytes(b'%PDF-1.4\nsynthetic test')
        self.source=SimpleNamespace(path=str(path),extension='.pdf',size=path.stat().st_size)

    @patch('intake.gemini.urlopen')
    def test_request_uses_header_auth_and_native_pdf_and_validates_json(self,send):
        response={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(AI_DOCUMENT)}]}}],
                  'usageMetadata':{'promptTokenCount':20,'candidatesTokenCount':30,'totalTokenCount':50}}
        send.return_value=BytesIO(json.dumps(response).encode())
        output=analyze_source(self.source,{})
        request=send.call_args.args[0];body=json.loads(request.data)
        self.assertNotIn('server-only-test-key',request.full_url)
        self.assertEqual(request.get_header('X-goog-api-key'),'server-only-test-key')
        self.assertEqual(body['contents'][0]['parts'][1]['inlineData']['mimeType'],'application/pdf')
        self.assertNotIn('maxItems',body['generationConfig']['responseSchema']['properties']['lines'])
        self.assertEqual(output['result']['fields']['po_number']['value'],'AI-001')
        self.assertEqual(output['usage']['total'],50)

    @patch('intake.gemini.urlopen')
    def test_quota_error_is_actionable_and_never_echoes_credentials(self,send):
        send.side_effect=HTTPError('https://generativelanguage.googleapis.com/',429,'quota',{},BytesIO(b'server-only-test-key'))
        with self.assertRaises(ValidationError) as caught:analyze_source(self.source,{})
        self.assertIn('한도',str(caught.exception));self.assertNotIn('server-only-test-key',str(caught.exception))

    @patch('intake.gemini.urlopen')
    def test_truncated_or_non_json_responses_do_not_produce_proposals(self,send):
        for response in [{'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'{"lines":['}]}}]},{}]:
            send.return_value=BytesIO(json.dumps(response).encode())
            with self.assertRaises(ValidationError):analyze_source(self.source,{})

    def test_item_limit_is_enforced_locally_without_expanding_provider_schema(self):
        with self.assertRaises(ValidationError):
            normalize_proposal({**AI_DOCUMENT,'lines':AI_DOCUMENT['lines']*201},{})

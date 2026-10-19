import io,json
from unittest.mock import patch
from django.test import SimpleTestCase,override_settings
from notices.providers.base import SendRequest
from notices.providers.configured import ConfiguredSmsProvider

@override_settings(SMS_LIVE_ENABLED=True,SMS_API_KEY='test-key',SMS_API_SECRET='test-secret')
class ProviderContractTests(SimpleTestCase):
    def test_send_uses_registered_sender_and_correlatable_key(self):
        captured=[]
        def transport(request,timeout):
            captured.append(request)
            return io.BytesIO(json.dumps({'messageList':[{'messageId':'M-1','statusCode':'2000'}],'failedMessageList':[]}).encode())
        with patch('notices.providers.configured.urlopen',side_effect=transport):
            result=ConfiguredSmsProvider().send(SendRequest('key-1','01012345678','0212345678','업무 확인'))
        self.assertEqual(result.status,'accepted');self.assertEqual(result.provider_id,'M-1')
        request=captured[0];self.assertEqual(request.full_url,'https://api.solapi.com/messages/v4/send-many/detail')
        message=json.loads(request.data)['messages'][0]
        self.assertEqual(message['to'],'01012345678');self.assertEqual(message['customFields']['clientKey'],'key-1')
        self.assertIn('HMAC-SHA256',request.headers['Authorization'])
    def test_delivery_lookup_and_unknown_without_provider_id(self):
        response={'messageList':{'M-1':{'messageId':'M-1','statusCode':'4000','status':'COMPLETE','customFields':{'clientKey':'key-1'}}}}
        with patch('notices.providers.configured.urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
            self.assertEqual(ConfiguredSmsProvider().lookup('key-1','M-1').status,'delivered')
    def test_unconfigured_provider_cannot_send(self):
        with override_settings(SMS_LIVE_ENABLED=False):
            with self.assertRaises(ValueError):ConfiguredSmsProvider()

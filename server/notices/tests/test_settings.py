import json
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from notices.models import NoticeSettings
class SettingsTests(TestCase):
    def setUp(self):
        self.owner=get_user_model().objects.create_user('owner');self.other=get_user_model().objects.create_user('other')
        NoticeSettings.objects.create(id=1,user=self.owner,recipient='01012345678',sender='0212345678')
    def test_owner_can_save_and_keys_are_never_rendered(self):
        self.client.force_login(self.owner)
        with override_settings(SMS_API_KEY='private-test-key',SMS_API_SECRET='private-test-secret'):
            response=self.client.get('/settings/notices/')
            self.assertEqual(response.status_code,200);self.assertNotContains(response,'private-test-key');self.assertNotContains(response,'private-test-secret')
            response=self.client.post('/settings/notices/',data=json.dumps({'recipient':'010-1111-2222','sender':'02-1234-5678','enabled':True}),content_type='application/json')
            self.assertEqual(response.status_code,200)
        self.assertEqual(NoticeSettings.objects.get().recipient,'01011112222')
    def test_other_user_cannot_change_owner_number(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post('/settings/notices/',data=json.dumps({'recipient':'01011112222'}),content_type='application/json').status_code,403)
    def test_invalid_phone_rejected(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post('/settings/notices/',data=json.dumps({'recipient':'abc','sender':'02','enabled':True}),content_type='application/json').status_code,422)

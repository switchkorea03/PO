from django.test import TestCase
from django.contrib.auth import get_user_model
class AccessTests(TestCase):
    def test_private_pages_require_login(self):
        for url in ["/orders/","/calendar/","/settings/notices/","/notices/history/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code,302)
    def test_staff_cannot_manage_users(self):
        user=get_user_model().objects.create_user("staff",password="test-pass-123")
        self.client.force_login(user)
        self.assertNotEqual(self.client.get("/admin/auth/user/").status_code,200)
    def test_registered_users_share_orders(self):
        user=get_user_model().objects.create_user("staff",password="test-pass-123")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/orders/").status_code,200)

from .settings import *
DATABASES={"default":{**DATABASES["default"],"NAME":"po_calendar_e2e"}}
SMS_PROVIDER="fake"
SMS_LIVE_ENABLED=False
PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
PRIVATE_MEDIA_ROOT=BASE_DIR.parent/".runtime"/"e2e-media"

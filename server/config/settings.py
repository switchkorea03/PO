import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.getenv('ENV_FILE',str(BASE_DIR / '.env')))
DEBUG = os.getenv("DEBUG", "1") == "1"
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-before-deployment-po-calendar")
if not DEBUG and SECRET_KEY.startswith("development-"):
    raise RuntimeError("운영 SECRET_KEY를 설정하세요.")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","accounts","orders","work","intake","notices"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default":{"ENGINE":"django.db.backends.postgresql","NAME":os.getenv("PGDATABASE","po_calendar"),"USER":os.getenv("PGUSER","po_app"),"PASSWORD":os.getenv("PGPASSWORD",""),"HOST":os.getenv("PGHOST","127.0.0.1"),"PORT":os.getenv("PGPORT","55432"),"CONN_MAX_AGE":0,"OPTIONS":{"connect_timeout":5}}}
TIME_ZONE="Asia/Seoul"
USE_TZ=True
LANGUAGE_CODE="ko-kr"
STATIC_URL="/static/"
STATICFILES_DIRS=[BASE_DIR/"static"]
STATIC_ROOT=BASE_DIR/"staticfiles"
PRIVATE_MEDIA_ROOT=Path(os.getenv("PRIVATE_MEDIA_ROOT", str(BASE_DIR/"private_media")))
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="/accounts/login/"
LOGIN_REDIRECT_URL="/calendar/"
LOGOUT_REDIRECT_URL="/accounts/login/"
AUTH_PASSWORD_VALIDATORS=[{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"}]
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SECURE_SSL_REDIRECT=not DEBUG
SECURE_HSTS_SECONDS=31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS=not DEBUG
SECURE_HSTS_PRELOAD=not DEBUG
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
CSRF_TRUSTED_ORIGINS=[v for v in os.getenv("CSRF_TRUSTED_ORIGINS","").split(",") if v]
DATA_UPLOAD_MAX_MEMORY_SIZE=22*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE=2*1024*1024
SMS_PROVIDER=os.getenv("SMS_PROVIDER","unconfigured")
SMS_API_KEY=os.getenv("SMS_API_KEY","")
SMS_API_SECRET=os.getenv("SMS_API_SECRET","")
SMS_LIVE_ENABLED=os.getenv("SMS_LIVE_ENABLED","0")=="1"
MAINTENANCE_FILE=BASE_DIR.parent/'.runtime'/'maintenance'
MIDDLEWARE.insert(1,'common.maintenance.MaintenanceMiddleware')

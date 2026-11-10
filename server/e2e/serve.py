import os,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from dotenv import dotenv_values
import psycopg
v=dotenv_values(root/".env")
with psycopg.connect(host=v['PGHOST'],port=v['PGPORT'],user=v['PGUSER'],password=v['PGPASSWORD'],dbname='postgres',autocommit=True,connect_timeout=5) as c:
    if not c.execute("SELECT 1 FROM pg_database WHERE datname='po_calendar_e2e'").fetchone():c.execute('CREATE DATABASE po_calendar_e2e')
os.environ['DJANGO_SETTINGS_MODULE']='config.e2e_settings'
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['NAME']=='po_calendar_e2e'
from django.core.management import call_command
call_command('migrate',interactive=False,verbosity=0)
call_command('flush',interactive=False,verbosity=0)
call_command('seed_po_defaults',verbosity=0)
from django.contrib.auth import get_user_model
get_user_model().objects.create_user('e2e-manager',password='local-e2e-password',is_staff=True,is_superuser=True)
import threading,time
def extraction_loop():
    from django.db import close_old_connections
    from intake.worker import run_pending
    while True:
        close_old_connections()
        run_pending()
        time.sleep(1)
threading.Thread(target=extraction_loop,daemon=True).start()
call_command('runserver','127.0.0.1:8001',use_reloader=False)

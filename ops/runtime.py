"""Local process setup. All downloaded binaries/data remain under the workspace."""
import os,sys,subprocess,json,secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SERVER=ROOT/'server'

def prepare():
    runtime=ROOT/'.runtime';runtime.mkdir(exist_ok=True)
    if os.name=='nt':
        drive=Path('P:/')
        if drive.exists():
            if not os.path.samefile(drive,runtime):raise RuntimeError('P: 드라이브가 다른 경로에 사용 중입니다. 매핑을 임의로 바꾸지 않습니다.')
        else:subprocess.run(['subst','P:',str(runtime)],check=True,capture_output=True)
        pg_bin=drive/'postgresql/pgsql/bin';pg_data=drive/'pgdata'
    else:pg_bin=Path(os.getenv('PG_BIN','/usr/bin'));pg_data=runtime/'pgdata'
    if not pg_data.exists():raise RuntimeError('로컬 PostgreSQL 데이터가 없습니다. README의 초기 환경 준비를 확인하세요.')
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    ctl=str(pg_bin/('pg_ctl.exe' if os.name=='nt' else 'pg_ctl'))
    # A PostgreSQL process started in a different Windows logon token may not
    # be inspectable through pg_ctl status. Verify the actual DB connection.
    from dotenv import dotenv_values
    import psycopg
    cfg=dotenv_values(SERVER/'.env')
    ready=False
    try:
        with psycopg.connect(host=cfg.get('PGHOST','127.0.0.1'),port=cfg.get('PGPORT','55432'),user=cfg.get('PGUSER','po_app'),password=cfg.get('PGPASSWORD',''),dbname='postgres',connect_timeout=3):ready=True
    except psycopg.OperationalError:pass
    if not ready:
        # On Windows server descendants may inherit PIPE handles and keep
        # communicate() waiting even after pg_ctl has exited. Use a real file.
        with (runtime/'pg-control.log').open('ab') as log:
            result=subprocess.run([ctl,'-D',str(pg_data),'-l',str((drive if os.name=='nt' else runtime)/'postgres.log'),'-w','start'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=40,**options)
        if result.returncode:raise RuntimeError('PostgreSQL 시작 실패: .runtime/pg-control.log를 확인하세요.')
    print('로컬 PostgreSQL 준비 완료: 127.0.0.1:55432')

def bootstrap_user():
    sys.path.insert(0,str(SERVER));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate',interactive=False,verbosity=0)
    from django.contrib.auth import get_user_model
    if get_user_model().objects.exists():return
    password=secrets.token_urlsafe(18)
    get_user_model().objects.create_superuser('po-admin',email='',password=password)
    (ROOT/'.runtime/local-login.txt').write_text('로컬 검토용 로그인\n주소: http://127.0.0.1:8000/\n사용자 이름: po-admin\n비밀번호: '+password+'\n',encoding='utf-8')
    print('초기 계정을 만들었습니다. .runtime/local-login.txt에서 확인하세요.')

if __name__=='__main__':
    try:
        prepare()
        if '--bootstrap-user' in sys.argv:bootstrap_user()
    except Exception as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)

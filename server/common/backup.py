"""Consistent PostgreSQL snapshot + protected-source backup and isolated restore."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
import psycopg
from psycopg import sql
from django.conf import settings
from django.db import connection,transaction
from orders.models import Order
from work.models import Task
from intake.models import SourceFile

def _hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()
def _binary(name):
    directory=Path(os.getenv('PG_BIN',str(settings.BASE_DIR.parent/'.runtime/postgresql/pgsql/bin')))
    executable=directory/(name+'.exe' if os.name=='nt' else name)
    if not executable.exists():raise ValueError(f'{name} 실행 경로를 PG_BIN에 설정하세요.')
    return str(executable)
def _env():
    cfg=connection.settings_dict
    return {**os.environ,'PGHOST':str(cfg['HOST']),'PGPORT':str(cfg['PORT']),'PGUSER':str(cfg['USER']),'PGPASSWORD':str(cfg['PASSWORD'])}
def _connect(database,autocommit=False):
    cfg=connection.settings_dict
    return psycopg.connect(host=cfg['HOST'],port=cfg['PORT'],user=cfg['USER'],password=cfg['PASSWORD'],dbname=database,autocommit=autocommit,connect_timeout=5)

def create_backup(destination):
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('백업은 새 디렉터리에만 생성합니다.')
    flag=Path(settings.MAINTENANCE_FILE);flag.parent.mkdir(parents=True,exist_ok=True)
    try:
        with flag.open('x',encoding='utf-8') as stream:stream.write('backup in progress')
    except FileExistsError:raise ValueError('이미 점검·백업 중입니다.')
    try:
        destination.mkdir(parents=True);media=destination/'media';media.mkdir()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
                tables=[row[0] for row in cursor.fetchall()]
                if tables:cursor.execute('LOCK TABLE '+','.join(connection.ops.quote_name(name) for name in tables)+' IN SHARE MODE')
                cursor.execute('SELECT pg_export_snapshot()');snapshot=cursor.fetchone()[0]
            files=[]
            for source in SourceFile.objects.all():
                path=Path(source.path).resolve()
                if not path.is_relative_to(Path(settings.PRIVATE_MEDIA_ROOT).resolve()) or _hash(path)!=source.sha256:raise ValueError('원본 파일 경로·해시 검증 실패')
                filename=str(source.id)+source.extension;shutil.copyfile(path,media/filename)
                files.append({'source_id':str(source.id),'filename':filename,'sha256':source.sha256})
            manifest={'database':connection.settings_dict['NAME'],'counts':{'orders':Order.objects.count(),'sources':SourceFile.objects.count(),'tasks':Task.objects.count()},'completed_task_ids':sorted(str(v) for v in Task.objects.filter(state='done').values_list('id',flat=True)),'files':files}
            subprocess.run([_binary('pg_dump'),'--format=custom','--no-owner','--snapshot='+snapshot,'--file='+str(destination/'database.dump'),connection.settings_dict['NAME']],env=_env(),check=True,capture_output=True,timeout=300)
        manifest['dump_sha256']=_hash(destination/'database.dump')
        (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        return manifest
    finally:flag.unlink(missing_ok=True)

def restore_backup(source,target_database,target_media):
    source=Path(source).resolve();target_media=Path(target_media).resolve()
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}_restore',target_database) or target_database==connection.settings_dict['NAME']:raise ValueError('복구 DB는 운영 DB와 다른 새 *_restore 이름이어야 합니다.')
    if target_media==Path(settings.PRIVATE_MEDIA_ROOT).resolve() or target_media.exists():raise ValueError('복구 media는 기존 경로와 다른 새 디렉터리여야 합니다.')
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    if _hash(source/'database.dump')!=manifest['dump_sha256']:raise ValueError('DB 백업 해시 불일치')
    for item in manifest['files']:
        path=(source/'media'/item['filename']).resolve()
        if not path.is_relative_to(source/'media') or _hash(path)!=item['sha256']:raise ValueError('파일 백업 해시 불일치')
    with _connect('postgres',True) as admin:
        exists=admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(target_database,)).fetchone()
        if not exists:admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target_database)))
    with _connect(target_database,True) as target:
        if target.execute("SELECT 1 FROM pg_tables WHERE schemaname='public'").fetchone():raise ValueError('복구 대상 DB가 비어 있지 않습니다.')
    subprocess.run([_binary('pg_restore'),'--no-owner','--no-privileges','--exit-on-error','--dbname='+target_database,str(source/'database.dump')],env=_env(),check=True,capture_output=True,timeout=300)
    target_media.mkdir(parents=True)
    with _connect(target_database) as target:
        for item in manifest['files']:
            path=target_media/item['filename'];shutil.copyfile(source/'media'/item['filename'],path)
            target.execute('UPDATE intake_sourcefile SET path=%s WHERE id=%s',(str(path),item['source_id']))
        target.execute('UPDATE notices_noticesettings SET enabled=false')
        counts={'orders':target.execute('SELECT count(*) FROM orders_order').fetchone()[0],'sources':target.execute('SELECT count(*) FROM intake_sourcefile').fetchone()[0],'tasks':target.execute('SELECT count(*) FROM work_task').fetchone()[0]}
        completed=sorted(str(row[0]) for row in target.execute("SELECT id FROM work_task WHERE state='done'").fetchall())
    if counts!=manifest['counts'] or completed!=manifest['completed_task_ids']:raise ValueError('복구 데이터 검증 실패')
    return {'counts':counts,'completed_task_ids':completed,'verified_files':len(manifest['files']),'sms_enabled':False}

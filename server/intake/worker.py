import json,subprocess,sys
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from django.db import transaction
from django.utils import timezone
from .models import ExtractionJob,ExtractionDraft

def process_extraction(job_id):
    with transaction.atomic():
        job=ExtractionJob.objects.select_for_update().select_related('source').get(pk=job_id)
        if job.status in ('done','failed'):return job.draft
        if job.status=='running' and job.lease_until and job.lease_until>timezone.now():return None
        job.status='running';job.attempts+=1;job.started_at=timezone.now();job.lease_until=timezone.now()+timedelta(seconds=150);job.save()
        path=job.source.path;extension=job.source.extension
    error=''
    try:
        completed=subprocess.run([sys.executable,str(Path(__file__).with_name('extract_cli.py')),path,extension],capture_output=True,text=True,encoding='utf-8',timeout=120)
        if completed.returncode:raise ValueError(completed.stderr.strip()[-1200:] or '인식 실패')
        result=json.loads(completed.stdout)
    except (ValueError,subprocess.SubprocessError,OSError) as exc:
        error=str(exc)
        result={'fields':{},'lines':[],'warnings':['파일을 판독하지 못했습니다. 수동입력으로 등록하세요.',error],'status':'failed','evidence':[]}
    with transaction.atomic():
        job=ExtractionJob.objects.select_for_update().get(pk=job_id)
        draft,_=ExtractionDraft.objects.get_or_create(job=job,defaults={'result':result})
        job.status='failed' if error else 'done';job.error=error;job.finished_at=timezone.now();job.lease_until=None;job.save()
        return draft

def run_pending():
    from common.maintenance import is_maintenance
    if is_maintenance():return 0
    now=timezone.now()
    from django.db.models import Q
    ids=list(ExtractionJob.objects.filter(Q(status='pending')|Q(status='running',lease_until__lt=now)).values_list('id',flat=True)[:10])
    for job_id in ids:process_extraction(job_id)
    return len(ids)

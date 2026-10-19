from datetime import time
from django.db import transaction
from common.clock import KST
from orders.models import ChangeEvent
from work.queries import get_notice_candidates
from .models import NoticeSettings,NoticeBatch,NoticeItem,DailyRun,EventCursor

def _settings():return NoticeSettings.objects.select_for_update().filter(pk=1,enabled=True).first()
def _new_batch(settings,on,kind,key):
    return NoticeBatch.objects.create(settings=settings,business_date=on,kind=kind,key=key,recipient=settings.recipient,sender=settings.sender)

@transaction.atomic
def plan_daily(now):
    local=now.astimezone(KST)
    if local.weekday()>=5 or local.time()<time(9):return ()
    settings=_settings()
    if not settings or not settings.recipient or not settings.sender:return ()
    run,created=DailyRun.objects.get_or_create(settings=settings,business_date=local.date())
    if not created:return ()
    candidates=get_notice_candidates(local.date(),True)
    if not candidates:return ()
    batch=_new_batch(settings,local.date(),'daily',f'daily:{settings.pk}:{local.date()}')
    NoticeItem.objects.bulk_create([NoticeItem(batch=batch,task_id=item.id,notice_revision=item.notice_revision) for item in candidates])
    run.batch=batch;run.save(update_fields=['batch'])
    return (batch.id,)

@transaction.atomic
def consume_changes(now):
    local=now.astimezone(KST)
    if local.weekday()>=5 or local.time()<time(9):return ()
    settings=_settings()
    if not settings:return ()
    cursor,_=EventCursor.objects.select_for_update().get_or_create(pk=1)
    events=list(ChangeEvent.objects.select_for_update().filter(consumed_at__isnull=True,occurred_at__lte=now).order_by('id')[:1000])
    candidates={str(c.id):c for c in get_notice_candidates(local.date(),False)}
    newly={}
    for event in events:
        when=event.occurred_at.astimezone(KST)
        if when.date()==local.date() and when.time()>=time(9):
            for entry in event.eligibility:
                task_id=entry['task_id']
                if task_id in candidates and entry.get('effective_on')==str(local.date()):newly[task_id]=event.id
        cursor.last_event_id=event.id
    cursor.save()
    ChangeEvent.objects.filter(pk__in=[event.id for event in events]).update(consumed_at=now)
    if not newly:return ()
    covered=set(str(t) for t in NoticeItem.objects.filter(batch__settings=settings,batch__business_date=local.date()).exclude(batch__status__in=['cancelled','expired']).values_list('task_id',flat=True))
    newly={task_id:event_id for task_id,event_id in newly.items() if task_id not in covered}
    if not newly:return ()
    daily=NoticeBatch.objects.select_for_update().filter(settings=settings,business_date=local.date(),kind='daily',status='pending').first()
    batch=daily or _new_batch(settings,local.date(),'additional',f'additional:{settings.pk}:{local.date()}:{max(newly.values())}')
    NoticeItem.objects.bulk_create([NoticeItem(batch=batch,task_id=task_id,notice_revision=candidates[task_id].notice_revision,event_id=event_id) for task_id,event_id in newly.items()])
    return (batch.id,)

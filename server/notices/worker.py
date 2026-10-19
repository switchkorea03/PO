import uuid
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from common.clock import KST
from work.queries import get_notice_candidates
from .models import NoticeBatch,NoticePart,SendAttempt,WorkerHeartbeat
from .renderer import render_notice
from .providers.base import SendRequest,SendResult

FINAL={'delivered','accepted','cancelled','expired','failed'}

def _update_batch(batch_id,now):
    with transaction.atomic():
        batch=NoticeBatch.objects.select_for_update().get(pk=batch_id)
        parts=list(batch.parts.all());states={p.status for p in parts}
        if not parts:batch.status='cancelled'
        elif 'unknown' in states or 'sending' in states:batch.status='unknown'
        elif 'failed' in states:batch.status='failed'
        elif states<={'delivered','cancelled'}:batch.status='delivered'
        elif states<={'accepted','delivered','cancelled'}:batch.status='accepted'
        else:batch.status='retry';batch.next_attempt_at=now+timedelta(minutes=5)
        batch.lease_until=None;batch.lease_token=None;batch.save()
        return batch.status

def dispatch_batch(batch_id,provider,now):
    local=now.astimezone(KST)
    with transaction.atomic():
        batch=NoticeBatch.objects.select_for_update(skip_locked=True).select_related('settings').filter(pk=batch_id).first()
        if not batch:return 'busy'
        if batch.status in FINAL:return batch.status
        if batch.status=='unknown':return 'unknown'
        if batch.status=='sending':
            if batch.lease_until and batch.lease_until>now:return 'busy'
            batch.status='unknown';batch.save(update_fields=['status']);return 'unknown'
        if local.weekday()>=5:return 'weekend'
        if batch.business_date!=local.date():batch.status='expired';batch.save(update_fields=['status']);return 'expired'
        if batch.next_attempt_at and batch.next_attempt_at>now:return 'waiting'
        if not batch.settings.enabled:batch.status='cancelled';batch.save(update_fields=['status']);return 'cancelled'
        ids=set(batch.items.values_list('task_id',flat=True))
        candidates=tuple(c for c in get_notice_candidates(local.date(),True) if c.id in ids)
        if not candidates:
            batch.status='cancelled';batch.save(update_fields=['status']);return 'cancelled'
        body=render_notice(candidates,local.date())
        parts=list(batch.parts.all())
        if parts and batch.body!=body:
            if any(p.status in ('accepted','delivered') for p in parts):
                # Already accepted parts cannot be retracted or safely re-segmented.
                batch.status='failed';batch.error='일부 접수 후 업무 내용이 변경되어 남은 분할 문자 확인이 필요합니다.';batch.save();return 'failed'
            total=max((p.attempts for p in parts),default=0)
            if total>=4:batch.status='failed';batch.save();return 'failed'
            # Only definitively failed, unaccepted requests are replaced.
            for part in parts:
                part.status='cancelled';part.save(update_fields=['status'])
            offset=max(p.position for p in parts)+1
            parts=[NoticePart.objects.create(batch=batch,position=offset+i,body=text,attempts=total) for i,text in enumerate(provider.split(body))]
        elif not parts:
            parts=[NoticePart.objects.create(batch=batch,position=i,body=text) for i,text in enumerate(provider.split(body))]
        batch.body=body;batch.status='sending';batch.lease_token=uuid.uuid4();batch.lease_until=now+timedelta(minutes=3);batch.save()
        token=batch.lease_token
    for part in parts:
        with transaction.atomic():
            batch=NoticeBatch.objects.select_for_update().get(pk=batch_id)
            if batch.lease_token!=token:return 'busy'
            part=NoticePart.objects.select_for_update().get(pk=part.id)
            if part.status in ('accepted','delivered','cancelled'):continue
            if part.status in ('unknown','sending'):continue
            if part.attempts>=4:part.status='failed';part.save();continue
            # Query again immediately before each network request.
            current_candidates=tuple(c for c in get_notice_candidates(local.date(),True) if c.id in ids)
            current_ids={c.id for c in current_candidates}
            if not ids.intersection(current_ids):part.status='cancelled';part.save();continue
            if render_notice(current_candidates,local.date())!=batch.body:
                batch.status='failed';batch.error='분할 발송 중 업무가 변경되어 남은 문자 확인이 필요합니다.'
                batch.lease_until=None;batch.lease_token=None;batch.save()
                batch.parts.filter(status__in=['pending','retry']).update(status='failed',reason=batch.error)
                return 'failed'
            part.attempts+=1;part.status='sending';part.save()
            attempt=SendAttempt.objects.create(part=part,number=part.attempts,requested_at=now)
            request=SendRequest(str(part.client_key),batch.recipient,batch.sender,part.body)
        try:result=provider.send(request)
        except Exception:result=SendResult('unknown',None,'네트워크 결과 미확정 · 발송 내역 확인 필요')
        with transaction.atomic():
            part=NoticePart.objects.select_for_update().get(pk=part.id)
            part.provider_id=result.provider_id;part.reason=result.reason or ''
            part.status=('retry' if part.attempts<4 else 'failed') if result.status=='failed' else result.status
            if part.status not in ('retry','failed','accepted','delivered','unknown'):part.status='unknown'
            part.save()
            attempt.status=result.status;attempt.reason=part.reason;attempt.provider_id=part.provider_id;attempt.finished_at=now;attempt.save()
    return _update_batch(batch_id,now)

def recover_unknown(provider,now):
    recovered=0
    expired=list(NoticeBatch.objects.filter(status='sending',lease_until__lte=now).values_list('id',flat=True))
    for batch_id in expired:
        with transaction.atomic():
            batch=NoticeBatch.objects.select_for_update().get(pk=batch_id)
            if batch.status=='sending' and batch.lease_until and batch.lease_until<=now:
                batch.parts.filter(status='sending').update(status='unknown')
                batch.status='unknown';batch.lease_token=None;batch.lease_until=None;batch.save()
    batch_ids=set()
    for part in NoticePart.objects.filter(status__in=['unknown','accepted']).select_related('batch'):
        try:status=provider.lookup(str(part.client_key),part.provider_id)
        except Exception:continue
        if status.status=='unknown':continue
        with transaction.atomic():
            current=NoticePart.objects.select_for_update().get(pk=part.id)
            if current.status not in ('unknown','accepted'):continue
            current.status=('retry' if current.attempts<4 else 'failed') if status.status=='failed' else status.status
            current.provider_id=status.provider_id or current.provider_id;current.reason=status.reason or '';current.save()
            current.history.filter(status__in=['sending','unknown','accepted']).update(status=status.status,provider_id=current.provider_id,finished_at=now)
            batch_ids.add(current.batch_id);recovered+=1
    for batch_id in batch_ids:_update_batch(batch_id,now)
    return recovered

def run_once(provider,now=None):
    from common.maintenance import is_maintenance
    if is_maintenance():return 0
    from .planner import plan_daily,consume_changes
    now=now or timezone.now()
    WorkerHeartbeat.objects.update_or_create(name='notices',defaults={'updated_at':now})
    plan_daily(now);consume_changes(now);recover_unknown(provider,now)
    ids=list(NoticeBatch.objects.filter(status__in=['pending','retry','sending']).values_list('id',flat=True))
    for batch_id in ids:dispatch_batch(batch_id,provider,now)
    return len(ids)

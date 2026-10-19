import re
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render
from django.db import transaction
from common.http import endpoint,body
from common.errors import ValidationError
from .models import NoticeSettings,NoticeBatch,WorkerHeartbeat

@endpoint
def settings_page(request):
    owner=get_user_model().objects.filter(is_superuser=True).order_by('id').first() or request.user
    config,_=NoticeSettings.objects.get_or_create(pk=1,defaults={'user':owner})
    may_edit=request.user.is_superuser or config.user_id==request.user.id
    if request.method=='POST':
        if not may_edit:return JsonResponse({'error':'본인 또는 관리자만 수신번호를 바꿀 수 있습니다.'},status=403)
        data=body(request);recipient=re.sub(r'[-\s]','',str(data.get('recipient','')));sender=re.sub(r'[-\s]','',str(data.get('sender','')))
        if not re.fullmatch(r'01[016789]\d{7,8}',recipient):raise ValidationError('본인 휴대폰 번호를 확인하세요.')
        if not re.fullmatch(r'(?:0\d{8,10}|\d{8})',sender):raise ValidationError('사전 등록한 발신번호를 확인하세요.')
        with transaction.atomic():
            config=NoticeSettings.objects.select_for_update().get(pk=1)
            config.recipient=recipient;config.sender=sender;config.enabled=data.get('enabled') is True;config.save()
        return JsonResponse({'saved':True})
    ready=settings.SMS_PROVIDER=='solapi' and bool(settings.SMS_API_KEY and settings.SMS_API_SECRET and settings.SMS_LIVE_ENABLED)
    from common.clock import today_kst
    from django.utils import timezone
    from work.queries import get_notice_candidates
    from .renderer import render_notice
    on=today_kst(timezone.now());items=get_notice_candidates(on,True)
    preview=render_notice(items,on) if items else '오늘 및 이전 날짜에 미완료 업무가 없습니다.\n알릴 업무가 없으면 문자를 보내지 않습니다.'
    return render(request,'notices/settings.html',{'config':config,'may_edit':may_edit,'ready':ready,'provider':settings.SMS_PROVIDER,'heartbeat':WorkerHeartbeat.objects.filter(name='notices').first(),'message_preview':preview})

@endpoint
def history(request):
    batches=NoticeBatch.objects.prefetch_related('parts__history').order_by('-created_at')[:100]
    return render(request,'notices/history.html',{'batches':batches,'provider':settings.SMS_PROVIDER})

from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from common.clock import today_kst
from common.errors import ValidationError,VersionConflict
from .models import ExtractionDraft,GeminiReview,GeminiDailyUsage
from .gemini import analyze_source,GeminiLimitError


def analyze_draft(draft_id,actor_id,expected_version,consent):
    if consent is not True:raise ValidationError('Google로 파일을 전송하는 데 동의한 후 실행하세요.')
    if not settings.GEMINI_API_KEY:raise ValidationError('서버에 Gemini API 키를 설정하세요.')
    day=today_kst(timezone.now())
    with transaction.atomic():
        draft=ExtractionDraft.objects.select_for_update().select_related('job__source').get(pk=draft_id)
        if draft.confirmed_order_id or draft.row_version!=int(expected_version):
            raise VersionConflict('인식 정보가 변경되었습니다. 새로고침 후 다시 확인하세요.')
        if GeminiReview.objects.filter(draft=draft,status='running',created_at__gte=timezone.now()-timedelta(seconds=120)).exists():
            raise VersionConflict('이미 Gemini 인식을 실행 중입니다. 잠시 후 다시 확인하세요.')
        GeminiDailyUsage.objects.get_or_create(day=day)
        daily=GeminiDailyUsage.objects.select_for_update().get(day=day)
        if daily.calls>=settings.GEMINI_DAILY_LIMIT:
            raise GeminiLimitError('앱의 오늘 Gemini 실행 한도에 도달했습니다. 내일 다시 실행하거나 직접 입력하세요.')
        daily.calls+=1;daily.save(update_fields=['calls'])
        review=GeminiReview.objects.create(draft=draft,requested_by_id=actor_id,model=settings.GEMINI_MODEL,draft_version=draft.row_version,original_result=draft.result)
    try:
        proposal=analyze_source(draft.job.source,review.original_result)
        review.result=proposal['result'];review.usage=proposal['usage'];review.status='done'
        review.finished_at=timezone.now();review.save(update_fields=['result','usage','status','finished_at'])
    except Exception as exc:
        error=exc if isinstance(exc,ValidationError) else ValidationError('Gemini 응답을 처리하지 못했습니다. 기존 인식값으로 확인·입력하세요.')
        review.status='failed';review.error=str(error);review.finished_at=timezone.now()
        review.save(update_fields=['status','error','finished_at'])
        raise error from None
    return review,max(0,settings.GEMINI_DAILY_LIMIT-daily.calls)


def apply_review(draft_id,review_id,actor_id,expected_version):
    with transaction.atomic():
        draft=ExtractionDraft.objects.select_for_update().get(pk=draft_id)
        review=GeminiReview.objects.select_for_update().get(pk=review_id,draft=draft,requested_by_id=actor_id)
        if draft.confirmed_order_id or draft.row_version!=int(expected_version) or review.draft_version!=draft.row_version or review.status!='done':
            raise VersionConflict('적용할 인식 정보가 변경되었습니다. 새로고침 후 다시 확인하세요.')
        draft.result=review.result;draft.row_version+=1;draft.save(update_fields=['result','row_version'])
        review.status='applied';review.applied_at=timezone.now();review.save(update_fields=['status','applied_at'])
    return draft

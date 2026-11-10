from django.http import JsonResponse
from django.views.decorators.http import require_POST
from common.http import endpoint,body
from .ai_services import analyze_draft,apply_review

@endpoint
@require_POST
def analyze(request,draft_id):
    data=body(request)
    review,remaining=analyze_draft(draft_id,request.user.id,data.get('draft_version',0),data.get('consent'))
    return JsonResponse({'review_id':str(review.id),'proposal':review.result,'model':review.model,'usage':review.usage,'remaining_today':remaining,'draft_version':review.draft_version})

@endpoint
@require_POST
def apply(request,draft_id,review_id):
    data=body(request)
    apply_review(draft_id,review_id,request.user.id,data.get('draft_version',0))
    return JsonResponse({'url':f'/intake/{draft_id}/review/'})

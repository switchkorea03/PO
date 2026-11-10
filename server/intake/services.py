from pathlib import Path
from django.db import transaction
from django.db.models import Max
from common.errors import VersionConflict,ValidationError
from orders.models import Order
from orders.services import save_order,reregister_order
from common.audit import audit
from .models import SourceFile,ExtractionJob,ExtractionDraft,OrderSource
from .storage import validate_upload,write_private
from .extractors.base import UploadResult

def upload_source(file,actor_id):
    extension,content,digest=validate_upload(file)
    existing=SourceFile.objects.filter(sha256=digest).first()
    if existing:
        return UploadResult(existing.id,existing.job.id,tuple(existing.order_versions.values_list('order_id',flat=True)))
    path=write_private(content,extension)
    try:
        with transaction.atomic():
            source,created=SourceFile.objects.get_or_create(sha256=digest,defaults={'path':str(path),'extension':extension,'size':len(content),'original_name':Path(file.name).name[:250],'uploaded_by_id':actor_id})
            if not created:path.unlink(missing_ok=True)
            job,_=ExtractionJob.objects.get_or_create(source=source)
            return UploadResult(source.id,job.id,tuple(source.order_versions.values_list('order_id',flat=True)))
    except Exception:
        path.unlink(missing_ok=True)
        raise

@transaction.atomic
def confirm_draft(draft_id,data,actor_id,target_order_id,expected_order_version,expected_draft_version):
    draft=ExtractionDraft.objects.select_for_update().select_related('job__source').get(pk=draft_id)
    if draft.confirmed_order_id:
        if draft.confirmed_order.is_deleted:raise ValidationError('삭제된 PO입니다. 휴지통에서 복원한 뒤 확인하세요.')
        return draft.confirmed_order
    if draft.row_version!=expected_draft_version:raise VersionConflict('다른 사용자가 인식 결과를 수정했습니다.')
    if target_order_id:
        target=Order.objects.get(pk=target_order_id)
        if target.customer_id!=data.customer_id or target.po_number!=data.po_number:raise ValidationError('수정본의 고객·PO 번호가 기존 PO와 다릅니다.')
    if target_order_id and (target.is_deleted or target.cancelled):
        order=reregister_order(target_order_id,data,actor_id,expected_order_version)
    else:
        order=save_order(data,actor_id,expected_order_version,target_order_id)
    version=(order.source_versions.aggregate(v=Max('version'))['v'] or 0)+1
    OrderSource.objects.get_or_create(order=order,source=draft.job.source,defaults={'version':version,'confirmed_by_id':actor_id})
    draft.confirmed_order=order;draft.row_version+=1;draft.save()
    audit(order,actor_id,'confirm_source',draft.job.source_id,after={'version':version,'extracted':draft.result})
    return order

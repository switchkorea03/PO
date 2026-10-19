from pathlib import Path
from datetime import date
from django.http import JsonResponse,FileResponse
from django.shortcuts import render,redirect
from django.conf import settings
from common.http import endpoint,body
from common.errors import ValidationError
from common.clock import today_kst
from django.utils import timezone
from orders.models import Customer,Order
from orders.forms import order_input
from .models import SourceFile,ExtractionJob,ExtractionDraft
from .services import upload_source,confirm_draft

@endpoint
def upload(request):
    if request.method=='POST':
        if 'file' not in request.FILES:raise ValidationError('PO 파일을 선택하세요.')
        result=upload_source(request.FILES['file'],request.user.id)
        if result.duplicate_order_ids:
            return render(request,'intake/upload.html',{'duplicates':Order.objects.filter(id__in=result.duplicate_order_ids),'source_id':result.source_id})
        return redirect(f'/intake/jobs/{result.job_id}/')
    return render(request,'intake/upload.html')

@endpoint
def job_status(request,job_id):
    job=ExtractionJob.objects.select_related('source').get(pk=job_id)
    if job.status in ('done','failed'):return redirect(f'/intake/{job.draft.id}/review/')
    return render(request,'intake/wait.html',{'job':job})

@endpoint
def source_download(request,source_id):
    source=SourceFile.objects.get(pk=source_id);path=Path(source.path).resolve()
    if not path.is_relative_to(Path(settings.PRIVATE_MEDIA_ROOT).resolve()):raise ValidationError('파일 보관 경로를 확인하세요.')
    return FileResponse(path.open('rb'),as_attachment=True,filename=source.original_name)

@endpoint
def review(request,draft_id):
    draft=ExtractionDraft.objects.select_related('job__source').get(pk=draft_id)
    if draft.confirmed_order_id:return redirect(f'/orders/{draft.confirmed_order_id}/')
    fields=draft.result.get('fields',{})
    initial={key:value.get('value') for key,value in fields.items()}
    customer=Customer.objects.filter(name=initial.get('customer_name')).first()
    target=None
    if customer and initial.get('po_number'):target=Order.objects.filter(customer=customer,po_number=initial['po_number']).first()
    if request.GET.get('target'):
        target=Order.objects.select_related('customer').get(pk=request.GET['target']);customer=target.customer
    initial.update({'customer_id':str(customer.id) if customer else '', 'order_type':customer.default_type if customer else 'domestic','erp_type':target.erp_type if target else 'unspecified','received_on':initial.get('received_on') or today_kst(timezone.now()).isoformat(),'lines':[{key:value.get('value') for key,value in line.items()} for line in draft.result.get('lines',[])]})
    if target:
        initial.update({'target_order_id':str(target.id),'row_version':target.row_version,'po_number':target.po_number,'order_type':target.order_type,'received_on':target.received_on or initial['received_on']})
        existing=list(target.lines.all())
        initial['revision_lines']=[{'id':str(v.id),'label':f'{v.code} · {v.name} · {v.quantity} {v.unit}'} for v in existing]
        by_code={v.code:v for v in existing if v.code and sum(x.code==v.code for x in existing)==1}
        for line in initial['lines']:
            code=line.get('code')
            if code in by_code and sum(x.get('code')==code for x in initial['lines'])==1:line['id']=str(by_code[code].id)
    initial['draft_version']=draft.row_version
    return render(request,'intake/review.html',{'draft':draft,'source':draft.job.source,'customers':Customer.objects.all(),'target':target,'initial_data':initial,'warnings':draft.result.get('warnings',[]),'evidence':draft.result.get('evidence',[])})

@endpoint
def confirm(request,draft_id):
    if request.method!='POST':return JsonResponse({'error':'POST required'},status=405)
    data=body(request)
    order=confirm_draft(draft_id,order_input(data),request.user.id,data.get('target_order_id') or None,data.get('row_version'),int(data.get('draft_version',0)))
    return JsonResponse({'id':str(order.id),'url':f'/orders/{order.id}/'})

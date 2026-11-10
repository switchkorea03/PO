from dataclasses import asdict
from django.http import JsonResponse,FileResponse
from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.http import require_POST,require_GET
from django.contrib import messages
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlsplit
from common.http import endpoint,body,parse_date
from common.errors import ValidationError
from .models import Customer,Order,OrderLine,Shipment
from .queries import search_orders
from .forms import order_input,shipment_input
from . import services

@endpoint
def list_orders(request):
    orders=search_orders(request.GET.get("q",""),request.GET.get("type"),request.GET.get("customer"),request.GET.get("state"))
    from work.queries import dashboard_summary
    from common.clock import today_kst
    from django.utils import timezone
    return render(request,"orders/list.html",{"orders":orders,"customers":Customer.objects.all(),'summary':dashboard_summary(today_kst(timezone.now()),request.GET.get('customer') or None,request.GET.get('type') or None)})

@endpoint
def new_order(request):
    if request.method=="POST":
        data=body(request);order=services.save_order(order_input(data),request.user.id,None)
        return JsonResponse({"id":str(order.id),"url":f"/orders/{order.id}/"})
    return render(request,"orders/form.html",{"customers":Customer.objects.order_by('default_type','name'),"order":None,"lines":[],"initial_data":{"lines":[]}})

@require_GET
@endpoint
def export_orders(request):
    from .exports import orders_workbook
    from common.clock import today_kst
    from django.utils import timezone
    orders=search_orders(request.GET.get('q',''),request.GET.get('type'),request.GET.get('customer'),request.GET.get('state'))
    response=FileResponse(orders_workbook(orders),as_attachment=True,
        filename=f'PO-list-{today_kst(timezone.now()):%Y%m%d}.xlsx',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Cache-Control']='private, no-store'
    return response

@endpoint
def edit_order(request,order_id,reregister=False):
    orders=Order.objects.select_related('customer')
    orders=orders.filter(Q(is_deleted=True)|Q(cancelled=True)) if reregister else orders.filter(is_deleted=False)
    order=orders.get(pk=order_id)
    if request.method=="POST":
        data=body(request)
        if reregister:
            order=services.reregister_order(order.id,order_input(data),request.user.id,data.get("row_version"))
        else:
            order=services.save_order(order_input(data),request.user.id,data.get("row_version"),order.id)
        return JsonResponse({"id":str(order.id),"url":f"/orders/{order.id}/"})
    initial={"customer_id":str(order.customer_id),"po_number":order.po_number,"order_type":order.order_type,"erp_type":order.erp_type,"ordered_on":order.ordered_on,"received_on":order.received_on,"contact":order.contact,"note":order.note,"row_version":order.row_version,"lines":[{"id":str(v.id),"code":v.code,"name":v.name,"quantity":str(v.quantity),"unit":v.unit,"unit_price":str(v.unit_price) if v.unit_price is not None else "","currency":v.currency,"source_amount":str(v.source_amount) if v.source_amount is not None else "","requested_due":v.requested_due} for v in order.lines.all()]}
    for line,values in zip(order.lines.all(),initial['lines']):values['internal_name']=line.internal_name
    return render(request,"orders/form.html",{"customers":Customer.objects.order_by('default_type','name'),"order":order,"initial_data":initial,"reregister":reregister})

@endpoint
def detail(request,order_id):
    order=Order.objects.select_related("customer").get(pk=order_id,is_deleted=False)
    shipments=[]
    for shipment in order.shipments.all():
        allocations={a.line_id:a.quantity for a in shipment.allocations.all()}
        shipments.append({"shipment":shipment,"rows":[{"line":line,"quantity":allocations.get(line.id,"")} for line in order.lines.all()]})
    return render(request,"orders/detail.html",{"order":order,"shipments":shipments,"tasks":order.tasks.prefetch_related("substeps"),"history":order.history.select_related("actor")[:50]})

@require_POST
@endpoint
def line_due(request,line_id):
    data=body(request)
    target=data.get('return_to','/orders/')
    if not (url_has_allowed_host_and_scheme(target,{request.get_host()}) and urlsplit(target).path=='/orders/'):
        target='/orders/'
    try:
        order=services.update_requested_due(line_id,parse_date(data.get('requested_due')),request.user.id,data.get('row_version'))
    except (ValidationError,ValueError) as exc:
        if request.content_type=='application/json':raise
        messages.error(request,str(exc) if isinstance(exc,ValidationError) else '납기일을 확인하세요.')
        return redirect(target)
    if request.content_type=='application/json':return JsonResponse({'id':str(line_id),'row_version':order.row_version})
    messages.success(request,'납기일을 저장했습니다.')
    return redirect(target)

@require_POST
@endpoint
def delete_order(request,order_id):
    try:
        order=services.delete_order(order_id,request.user.id,body(request).get('row_version'))
    except ValidationError as exc:
        if request.content_type=='application/json':raise
        messages.error(request,str(exc))
        return redirect('/orders/')
    if request.content_type!='application/json':
        messages.success(request,'PO를 휴지통으로 이동했습니다.')
        return redirect('/orders/')
    return JsonResponse({'id':str(order.id),'deleted':True,'url':'/orders/'})

@require_POST
@endpoint
def restore_order(request,order_id):
    order=services.restore_order(order_id,request.user.id,body(request).get('row_version'))
    return JsonResponse({'id':str(order.id),'deleted':False,'url':f'/orders/{order.id}/'})

@require_POST
@endpoint
def customer_create(request):
    data=body(request);name=data.get("name","").strip()
    if not name:raise ValidationError("고객명을 입력하세요.")
    customer=Customer(name=name,contact=data.get("contact",""),default_type=data.get("default_type","domestic"),currency=data.get("currency","KRW"))
    if customer.default_type not in ("domestic","overseas") or len(customer.currency)!=3:raise ValidationError("고객 기본값을 확인하세요.")
    customer.full_clean(validate_unique=False)
    customer,_=Customer.objects.get_or_create(name=name,defaults={'contact':customer.contact,'default_type':customer.default_type,'currency':customer.currency})
    return JsonResponse({"id":str(customer.id),"name":customer.name,"default_type":customer.default_type,"currency":customer.currency})

@require_POST
@endpoint
def shipment_save(request,order_id):
    data=body(request);shipment=services.save_shipment(order_id,shipment_input(data),request.user.id,data.get("row_version"))
    return JsonResponse({"id":str(shipment.id),"row_version":shipment.row_version})

@require_POST
@endpoint
def shipment_confirm(request,shipment_id):
    shipment=services.confirm_shipment(shipment_id,request.user.id,body(request).get("row_version"))
    return JsonResponse({"id":str(shipment.id),"completed":shipment.completed})

@require_POST
@endpoint
def shipment_correct(request,shipment_id):
    data=body(request);shipment=services.correct_shipment(shipment_id,shipment_input(data).allocations,data.get("reason",""),request.user.id,data.get("row_version"))
    return JsonResponse({"id":str(shipment.id)})

@require_POST
@endpoint
def cancel_remaining(request,line_id):
    data=body(request);line=services.cancel_remaining(line_id,data["quantity"],request.user.id,data.get("row_version"))
    return JsonResponse({"remaining":str(line.remaining)})

@require_POST
@endpoint
def cancel(request,order_id):
    order=services.cancel_order(order_id,request.user.id,body(request).get("row_version"))
    return JsonResponse({"cancelled":order.cancelled})

@require_POST
@endpoint
def shipment_cancel(request,shipment_id):
    data=body(request);shipment=services.cancel_shipment(shipment_id,data.get('reason',''),request.user.id,data.get('row_version'))
    return JsonResponse({'cancelled':shipment.cancelled})

@require_POST
@endpoint
def shipment_eta(request,shipment_id):
    data=body(request);shipment=services.update_eta(shipment_id,parse_date(data.get('eta')),request.user.id,data.get('row_version'))
    return JsonResponse({'eta':shipment.eta})

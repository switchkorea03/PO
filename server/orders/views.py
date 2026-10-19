from dataclasses import asdict
from django.http import JsonResponse
from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.http import require_POST
from common.http import endpoint,body,parse_date
from common.errors import ValidationError
from .models import Customer,Order,OrderLine,Shipment
from .queries import search_orders
from .forms import order_input,shipment_input
from . import services

@endpoint
def list_orders(request):
    orders=search_orders(request.GET.get("q",""),request.GET.get("type"),request.GET.get("customer"),request.GET.get("state"))
    return render(request,"orders/list.html",{"orders":orders,"customers":Customer.objects.all()})

@endpoint
def new_order(request):
    if request.method=="POST":
        data=body(request);order=services.save_order(order_input(data),request.user.id,None)
        return JsonResponse({"id":str(order.id),"url":f"/orders/{order.id}/"})
    return render(request,"orders/form.html",{"customers":Customer.objects.all(),"order":None,"lines":[],"initial_data":{"lines":[]}})

@endpoint
def edit_order(request,order_id):
    order=Order.objects.select_related("customer").get(pk=order_id)
    if request.method=="POST":
        data=body(request);order=services.save_order(order_input(data),request.user.id,data.get("row_version"),order.id)
        return JsonResponse({"id":str(order.id),"url":f"/orders/{order.id}/"})
    initial={"customer_id":str(order.customer_id),"po_number":order.po_number,"order_type":order.order_type,"erp_type":order.erp_type,"ordered_on":order.ordered_on,"received_on":order.received_on,"contact":order.contact,"note":order.note,"row_version":order.row_version,"lines":[{"id":str(v.id),"code":v.code,"name":v.name,"quantity":str(v.quantity),"unit":v.unit,"unit_price":str(v.unit_price) if v.unit_price is not None else "","currency":v.currency,"source_amount":str(v.source_amount) if v.source_amount is not None else "","requested_due":v.requested_due} for v in order.lines.all()]}
    return render(request,"orders/form.html",{"customers":Customer.objects.all(),"order":order,"initial_data":initial})

@endpoint
def detail(request,order_id):
    order=Order.objects.select_related("customer").get(pk=order_id)
    shipments=[]
    for shipment in order.shipments.all():
        allocations={a.line_id:a.quantity for a in shipment.allocations.all()}
        shipments.append({"shipment":shipment,"rows":[{"line":line,"quantity":allocations.get(line.id,"")} for line in order.lines.all()]})
    return render(request,"orders/detail.html",{"order":order,"shipments":shipments,"tasks":order.tasks.prefetch_related("substeps"),"history":order.history.select_related("actor")[:50]})

@require_POST
@endpoint
def customer_create(request):
    data=body(request);name=data.get("name","").strip()
    if not name:raise ValidationError("고객명을 입력하세요.")
    customer=Customer(name=name,contact=data.get("contact",""),default_type=data.get("default_type","domestic"),currency=data.get("currency","KRW"))
    if customer.default_type not in ("domestic","overseas") or len(customer.currency)!=3:raise ValidationError("고객 기본값을 확인하세요.")
    customer.full_clean();customer.save()
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

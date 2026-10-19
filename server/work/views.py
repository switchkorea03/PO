import calendar
from dataclasses import asdict
from datetime import date,timedelta
from collections import defaultdict
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST
from common.http import endpoint,body,parse_date
from common.clock import today_kst
from common.errors import ValidationError
from orders.models import Customer,OrderLine
from .models import Task
from .queries import list_tasks
from .rules import next_weekday
from . import services

def calendar_data(start,end,customer_id=None,order_type=None):
    tasks=list_tasks(start,end,customer_id,order_type)
    grouped=defaultdict(list)
    for task in tasks:grouped[(task.effective_on,str(task.kind))].append(task)
    groups=[]
    for (on,kind),items in grouped.items():
        names=sorted(set(t.customer_name for t in items))
        states=[t.state for t in items]
        state="done" if all(s=="done" for s in states) else ("cancelled" if all(s=="cancelled" for s in states) else ("partial" if any(s in ("partial","done") for s in states) else "open"))
        title=",".join(names)+"(출고 내역 공유)" if kind=="domestic_share" else (items[0].title+(f" · {len(items)}건" if len(items)>1 else ""))
        groups.append({"date":on,"kind":kind,"title":title,"state":state,"customers":names,"tasks":[asdict(t) for t in items]})
    lines=OrderLine.objects.select_related("order__customer").filter(order__order_type="domestic",order__cancelled=False,requested_due__isnull=False)
    if customer_id:lines=lines.filter(order__customer_id=customer_id)
    if order_type=="overseas":lines=lines.none()
    due=[]
    for line in lines:
        on=next_weekday(line.requested_due)
        if start<=on<=end:due.append({"id":f"due:{line.id}","date":on,"original_on":line.requested_due,"title":line.order.customer.name+"(납기)","checkable":False,"order_id":line.order_id,"line_name":line.name})
    return {"tasks":[asdict(t) for t in tasks],"groups":groups,"due_markers":due}

@endpoint
def calendar_api(request):
    start=date.fromisoformat(request.GET["start"]);end=date.fromisoformat(request.GET["end"])
    if end<start or (end-start).days>370:raise ValidationError("조회 기간은 최대 370일입니다.")
    return JsonResponse(calendar_data(start,end,request.GET.get("customer") or None,request.GET.get("type") or None))

@endpoint
def calendar_page(request):
    today=today_kst(timezone.now());selected=parse_date(request.GET.get("date")) or today
    mode=request.GET.get("view","month")
    if mode=="week":
        start=selected-timedelta(days=selected.weekday());weeks=[[start+timedelta(days=i) for i in range(7)]];previous=start-timedelta(days=7);following=start+timedelta(days=7)
    else:
        first=selected.replace(day=1);weeks=calendar.Calendar(0).monthdatescalendar(first.year,first.month);previous=(first-timedelta(days=1)).replace(day=1);following=(first+timedelta(days=32)).replace(day=1)
    data=calendar_data(weeks[0][0],weeks[-1][-1],request.GET.get("customer") or None,request.GET.get("type") or None)
    byday=defaultdict(list)
    for g in data["groups"]:byday[g["date"]].append(g)
    duebyday=defaultdict(list)
    for d in data["due_markers"]:duebyday[d["date"]].append(d)
    calendar_weeks=[[{"date":d,"groups":byday[d],"dues":duebyday[d],"today":d==today,"selected":d==selected,"outside":d.month!=selected.month} for d in week] for week in weeks]
    selected_tasks=Task.objects.select_related("order__customer").prefetch_related("substeps").filter(effective_on=selected)
    undated=Task.objects.select_related("order__customer").filter(effective_on__isnull=True,state__in=["open","partial"])
    if request.GET.get("customer"):selected_tasks=selected_tasks.filter(order__customer_id=request.GET["customer"]);undated=undated.filter(order__customer_id=request.GET["customer"])
    if request.GET.get("type") in ("domestic","overseas"):selected_tasks=selected_tasks.filter(order__order_type=request.GET["type"]);undated=undated.filter(order__order_type=request.GET["type"])
    notice_problems=[]
    try:
        from notices.models import NoticeBatch
        notice_problems=NoticeBatch.objects.filter(status__in=["failed","unknown"]).order_by("-created_at")[:3]
    except ImportError:pass
    return render(request,"work/calendar.html",{"today":today,"selected":selected,"mode":mode,"weeks":calendar_weeks,"previous":previous,"following":following,"selected_tasks":selected_tasks,"undated":undated,"customers":Customer.objects.all(),"notice_problems":notice_problems})

@endpoint
def task_detail(request,task_id):
    task=Task.objects.select_related("order__customer","shipment").prefetch_related("substeps").get(pk=task_id)
    if task.shipment:
        items=[{'code':a.line.code,'name':a.line.name,'quantity':a.quantity,'unit':a.line.unit} for a in task.shipment.allocations.select_related('line')]
    else:items=list(task.order.lines.values('code','name','quantity','unit'))
    return render(request,"work/detail.html",{"task":task,"item_rows":items,"today":today_kst(timezone.now())})

@require_POST
@endpoint
def task_move(request,task_id):
    data=body(request);result=services.move_task(task_id,parse_date(data.get("target_on")),request.user.id,data.get("row_version"));return JsonResponse(asdict(result))

@require_POST
@endpoint
def task_review(request,task_id):
    data=body(request);result=services.review_completed_task(task_id,bool(data.get("reopen")),request.user.id,data.get("row_version"));return JsonResponse(asdict(result))

@require_POST
@endpoint
def substep_check(request,substep_id):
    data=body(request);result=services.set_substep(substep_id,bool(data.get("done")),request.user.id,data.get("row_version"));return JsonResponse(asdict(result))

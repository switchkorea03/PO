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
from .queries import list_tasks,dashboard_summary
from .rules import next_weekday
from . import services
from .calendar_presentation import day_summary

def calendar_data(start,end,customer_id=None,order_type=None):
    tasks=list_tasks(start,end,customer_id,order_type)
    grouped=defaultdict(list)
    for task in tasks:grouped[(task.effective_on,str(task.kind))].append(task)
    groups=[]
    for (on,kind),items in grouped.items():
        names=sorted(set(t.customer_name for t in items))
        customer_count=len({t.customer_id for t in items})
        states=[t.state for t in items]
        state="done" if all(s=="done" for s in states) else ("cancelled" if all(s=="cancelled" for s in states) else ("partial" if any(s in ("partial","done") for s in states) else "open"))
        title=",".join(names)+"(출고 내역 공유)" if kind=="domestic_share" else items[0].title+f' · {customer_count}건'
        groups.append({"date":on,"kind":kind,"title":title,"state":state,"customers":names,'customer_count':customer_count,"tasks":[asdict(t) for t in items]})
    lines=OrderLine.objects.select_related("order__customer").filter(order__order_type="domestic",order__cancelled=False,order__is_deleted=False,requested_due__isnull=False)
    if customer_id:lines=lines.filter(order__customer_id=customer_id)
    if order_type=="overseas":lines=lines.none()
    due=[];due_groups=defaultdict(list)
    for line in lines:
        on=next_weekday(line.requested_due)
        if start<=on<=end:due_groups[(on,line.order.customer_id)].append(line)
    for (on,customer),items in due_groups.items():
        first=items[0];order_ids=list(dict.fromkeys(line.order_id for line in items))
        due.append({'id':f'due:{customer}:{on}','customer_id':str(customer),'customer_name':first.order.customer.name,'date':on,'original_on':min(line.requested_due for line in items),
            'title':first.order.customer.name+'(납기)','checkable':False,'order_id':order_ids[0],
            'order_ids':order_ids,'line_name':', '.join(line.code or line.name for line in items),
            'url':f'/orders/{order_ids[0]}/' if len(order_ids)==1 else f'/orders/?customer={customer}'})
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
    tasksbyday=defaultdict(list)
    for task in data['tasks']:tasksbyday[task['effective_on']].append(task)
    for week in calendar_weeks:
        for day in week:day.update(day_summary(tasksbyday[day['date']],day['dues'],day['date'],today))
    selected_tasks=Task.objects.select_related("order__customer").prefetch_related("substeps").filter(effective_on=selected,order__is_deleted=False)
    undated=Task.objects.select_related("order__customer").filter(effective_on__isnull=True,state__in=["open","partial"],order__is_deleted=False)
    if request.GET.get("customer"):selected_tasks=selected_tasks.filter(order__customer_id=request.GET["customer"]);undated=undated.filter(order__customer_id=request.GET["customer"])
    if request.GET.get("type") in ("domestic","overseas"):selected_tasks=selected_tasks.filter(order__order_type=request.GET["type"]);undated=undated.filter(order__order_type=request.GET["type"])
    notice_problems=[]
    try:
        from notices.models import NoticeBatch
        notice_problems=NoticeBatch.objects.filter(status__in=["failed","unknown"]).order_by("-created_at")[:3]
    except ImportError:pass
    summary=dashboard_summary(today,request.GET.get('customer') or None,request.GET.get('type') or None)
    selected_customer_count=selected_tasks.exclude(state='cancelled').order_by().values('order__customer_id').distinct().count()
    agenda_groups={}
    for task in selected_tasks.exclude(state='cancelled').order_by('order__customer__name','order__po_number','kind','id'):
        key=str(task.order.customer_id)
        group=agenda_groups.setdefault(key,{'name':task.order.customer.name,'tasks':[],'dues':[],'pending_count':0})
        group['tasks'].append(task)
        if task.state!='done' and not task.suspended:group['pending_count']+=1
    for due in duebyday[selected]:
        group=agenda_groups.setdefault(due['customer_id'],{'name':due['customer_name'],'tasks':[],'dues':[],'pending_count':0})
        group['dues'].append(due)
    selected_summary=day_summary(tasksbyday[selected],duebyday[selected],selected,today)
    cancelled_tasks=selected_tasks.filter(state='cancelled').order_by('order__customer__name','order__po_number','id')
    return render(request,"work/calendar.html",{"today":today,"selected":selected,"mode":mode,"weeks":calendar_weeks,"previous":previous,"following":following,"selected_tasks":selected_tasks,"undated":undated,"customers":Customer.objects.all(),"notice_problems":notice_problems,'summary':summary,'selected_customer_count':selected_customer_count,'agenda_groups':sorted(agenda_groups.values(),key=lambda group:(not group['pending_count'],group['name'])),'selected_summary':selected_summary,'cancelled_tasks':cancelled_tasks})

@endpoint
def task_detail(request,task_id):
    task=Task.objects.select_related("order__customer","shipment").prefetch_related("substeps").get(pk=task_id,order__is_deleted=False)
    if task.shipment:
        items=[{'code':a.line.code,'name':a.line.display_name,'quantity':a.quantity,'unit':a.line.unit} for a in task.shipment.allocations.select_related('line')]
    else:items=[{'code':line.code,'name':line.display_name,'quantity':line.quantity,'unit':line.unit} for line in task.order.lines.all()]
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

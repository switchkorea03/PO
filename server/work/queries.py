from common.contracts import TaskView,TaskKind,NoticeCandidate
from .models import Task

def dashboard_summary(on,customer_id=None,order_type=None):
    from orders.models import Shipment
    from orders.queries import search_orders
    pending=Task.objects.filter(state__in=['open','partial'],suspended=False,order__cancelled=False)
    undated=Shipment.objects.filter(order__order_type='overseas',order__cancelled=False,completed=False,cancelled=False,etd__isnull=True)
    if customer_id:
        pending=pending.filter(order__customer_id=customer_id)
        undated=undated.filter(order__customer_id=customer_id)
    if order_type in ('domestic','overseas'):
        pending=pending.filter(order__order_type=order_type)
        undated=undated.filter(order__order_type=order_type)
    return {'today':pending.filter(effective_on=on).count(),'overdue':pending.filter(effective_on__lt=on).count(),
            'open_orders':len(search_orders(order_type=order_type,customer_id=customer_id,state='open')),'undated_shipments':undated.count()}

def task_view(task):
    return TaskView(task.id,task.order_id,task.shipment_id,task.order.customer_id,task.order.customer.name,task.order.po_number,TaskKind(task.kind),task.title,task.effective_on,task.open_steps,task.state,task.suspended,task.notice_revision,task.row_version)

def list_tasks(start,end,customer_id=None,order_type=None):
    qs=Task.objects.select_related("order__customer").prefetch_related("substeps").filter(effective_on__gte=start,effective_on__lte=end)
    if customer_id:qs=qs.filter(order__customer_id=customer_id)
    if order_type:qs=qs.filter(order__order_type=order_type)
    return tuple(task_view(task) for task in qs)

def get_notice_candidates(on,include_overdue):
    qs=Task.objects.select_related("order__customer").prefetch_related("substeps").filter(state__in=["open","partial"],suspended=False,order__cancelled=False)
    qs=qs.filter(effective_on__lte=on) if include_overdue else qs.filter(effective_on=on)
    return tuple(NoticeCandidate(task.id,task.order.customer.name,task.order.po_number,task.title,task.effective_on,task.open_steps,task.notice_revision) for task in qs.order_by("effective_on","order__customer__name","kind","id"))

from django.db.models import Q
from .models import Order

def search_orders(query="",order_type=None,customer_id=None,state=None):
    qs=Order.objects.select_related("customer").prefetch_related("lines","shipments")
    qs=qs.filter(is_deleted=state=='deleted')
    if query:qs=qs.filter(Q(customer__name__icontains=query)|Q(po_number__icontains=query)|Q(lines__code__icontains=query)|Q(lines__name__icontains=query)|Q(lines__internal_name__icontains=query)).distinct()
    if order_type in ("domestic","overseas"):qs=qs.filter(order_type=order_type)
    if customer_id:qs=qs.filter(customer_id=customer_id)
    if state=="cancelled":qs=qs.filter(cancelled=True)
    elif state in ("open","done"):qs=qs.filter(cancelled=False)
    results=list(qs)
    if state=="open":results=[o for o in results if any(line.remaining>0 for line in o.lines.all())]
    if state=="done":results=[o for o in results if all(line.remaining==0 for line in o.lines.all())]
    return results

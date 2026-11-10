from django.shortcuts import render
from django.views.decorators.http import require_GET
from common.http import endpoint
from .queries import inventory_rows
from .providers import get_inventory_provider


@endpoint
@require_GET
def index(request):
    query=request.GET.get('q','').strip()[:200]
    rows=inventory_rows(query)
    return render(request,'inventory/list.html',{'rows':rows,'query':query,'provider':get_inventory_provider(),
        'item_count':len({row['item_name'] for row in rows}),'pending_count':sum(row['remaining']>0 for row in rows)})

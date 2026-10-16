from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from orders.models import Order
@login_required
def order_list(request):
    return HttpResponse("PO 목록\n"+"\n".join(str(v) for v in Order.objects.select_related("customer")))
@login_required
def work_calendar(request): return HttpResponse("업무 달력")
@login_required
def notice_settings(request): return HttpResponse("문자 서비스 미설정")

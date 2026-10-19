from pathlib import Path
from django.conf import settings
from django.http import HttpResponse
def is_maintenance():return Path(settings.MAINTENANCE_FILE).exists()
class MaintenanceMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if is_maintenance():return HttpResponse('백업·점검 중입니다. 잠시 후 다시 시도하세요.',status=503,content_type='text/plain; charset=utf-8')
        return self.get_response(request)

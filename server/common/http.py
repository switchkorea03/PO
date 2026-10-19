import json
from functools import wraps
from dataclasses import asdict,is_dataclass
from datetime import date
from decimal import Decimal,InvalidOperation
from uuid import UUID
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist,ValidationError as DjangoValidationError
from django.http import JsonResponse
from common.errors import ValidationError

def body(request):
    if request.content_type=="application/json":
        try:return json.loads(request.body)
        except (ValueError,TypeError):raise ValidationError("요청 JSON을 확인하세요.")
    return request.POST.dict()
def json_value(value):return asdict(value) if is_dataclass(value) else value

def endpoint(fn):
    @wraps(fn)
    @login_required
    def wrapped(request,*args,**kwargs):
        try:return fn(request,*args,**kwargs)
        except ValidationError as exc:return JsonResponse({"error":str(exc)},status=exc.status)
        except ObjectDoesNotExist:return JsonResponse({"error":"대상을 찾을 수 없습니다."},status=404)
        except DjangoValidationError as exc:return JsonResponse({"error":" / ".join(exc.messages)},status=422)
        except (ValueError,TypeError,KeyError,InvalidOperation) as exc:return JsonResponse({"error":"입력값·날짜·수량을 확인하세요."},status=422)
    return wrapped

def parse_date(value):return date.fromisoformat(value) if value else None

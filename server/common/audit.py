import json
from django.core.serializers.json import DjangoJSONEncoder
from orders.models import AuditEntry
def audit(order,actor_id,action,target,before=None,after=None,reason=""):
    normalize=lambda value:json.loads(json.dumps(value or {},cls=DjangoJSONEncoder))
    return AuditEntry.objects.create(order=order,actor_id=actor_id,action=action,target=str(target),before=normalize(before),after=normalize(after),reason=reason)

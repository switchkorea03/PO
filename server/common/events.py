from orders.models import ChangeEvent
def record_change(order_id,affected_task_ids,actor_id,occurred_at,eligibility=()):
    return ChangeEvent.objects.create(order_id=order_id,affected_task_ids=[str(v) for v in affected_task_ids],actor_id=actor_id,occurred_at=occurred_at,eligibility=list(eligibility)).public_id

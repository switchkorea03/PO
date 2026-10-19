import hashlib,json
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from common.contracts import OrderSnapshot,LineInput,ShipmentInput
from common.errors import ValidationError
from common.audit import audit
from common.events import record_change
from orders.models import Order,Shipment
from orders.services import check_version
from .models import Task,Substep
from .rules import build_task_specs
from .queries import task_view

def snapshot(order):
    lines=tuple(LineInput(v.id,v.code,v.name,v.quantity,v.unit,v.unit_price,v.currency,v.source_amount,v.requested_due) for v in order.lines.all())
    shipments=tuple(ShipmentInput(v.id,v.ship_on,v.etd,v.eta,{a.line_id:a.quantity for a in v.allocations.all()}) for v in order.shipments.filter(cancelled=False).prefetch_related("allocations"))
    currencies={line.currency for line in lines}
    return OrderSnapshot(order.id,order.order_type,order.erp_type,next(iter(currencies)) if len(currencies)==1 else "MIX",order.received_on,lines,shipments)

def _dependency(spec,snap):
    shipments=[s for s in snap.shipments if s.id==spec.shipment_id] if spec.shipment_id else list(snap.shipments)
    line_ids={k for s in shipments for k in s.allocations}
    payload={"basis":str(spec.basis_on),"allocations":[{str(k):str(v) for k,v in s.allocations.items()} for s in shipments],"lines":[asdict(line) for line in snap.lines if not spec.shipment_id or line.id in line_ids],"steps":spec.substeps}
    if spec.kind=="overseas_bl_eta":payload["etas"]=[str(s.eta) for s in shipments]
    return hashlib.sha256(json.dumps(payload,default=str,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def _eligible(task,before_on,before_state):
    if task.state in ("open","partial") and not task.suspended and task.effective_on and (task.effective_on!=before_on or before_state not in ("open","partial")):
        return {"task_id":str(task.id),"effective_on":str(task.effective_on),"revision":task.notice_revision}
    return None

@transaction.atomic
def reconcile_order(order_id,actor_id):
    order=Order.objects.select_for_update().select_related("customer").get(pk=order_id)
    snap=snapshot(order);active=set();changed=[];eligibility=[]
    for spec in build_task_specs(snap):
        scope=f"shipment:{spec.shipment_id}" if spec.shipment_id else f"order:{order.id}"
        task,created=Task.objects.select_for_update().get_or_create(scope_key=scope,kind=spec.kind,defaults={"order":order,"shipment_id":spec.shipment_id,"title":spec.title})
        active.add(task.id);old_on=task.effective_on;old_state=task.state;before=(task.basis_on,task.auto_on,task.title,task.dependency_hash,task.suspended,task.effective_on,task.state)
        dep=_dependency(spec,snap);dependency_changed=bool(task.dependency_hash and dep!=task.dependency_hash)
        if task.state=="done":
            if dependency_changed or order.cancelled:task.needs_review=True
        else:
            was_suspended=task.suspended
            task.suspended=spec.auto_on is None
            if order.cancelled:task.state="cancelled"
            if task.manual_on and (task.auto_on!=spec.auto_on or was_suspended):task.recalc_needed=True
            if was_suspended and spec.auto_on and task.manual_on:
                task.suspended=True;task.recalc_needed=True
            task.effective_on=None if task.suspended else (task.manual_on or spec.auto_on)
        task.basis_on=spec.basis_on;task.auto_on=spec.auto_on;task.title=spec.title;task.dependency_hash=dep
        after=(task.basis_on,task.auto_on,task.title,task.dependency_hash,task.suspended,task.effective_on,task.state)
        if created or before!=after:
            task.row_version+=0 if created else 1
            task.notice_revision+=0 if created else 1
            task.save();changed.append(task.id)
            candidate=_eligible(task,old_on,old_state)
            if candidate:eligibility.append(candidate)
        elif task.needs_review:task.save(update_fields=["needs_review"])
        if created:
            Substep.objects.bulk_create([Substep(task=task,label=label,position=i) for i,label in enumerate(spec.substeps)])
        elif task.state!="done":
            for i,label in enumerate(spec.substeps):
                step,_=Substep.objects.get_or_create(task=task,position=i,defaults={"label":label})
                if step.label!=label:
                    step.label=label;step.save(update_fields=["label"])
    for task in order.tasks.exclude(pk__in=active):
        if task.state=="done":
            if not task.needs_review:task.needs_review=True;task.save(update_fields=["needs_review"])
        elif task.state!="cancelled":task.state="cancelled";task.row_version+=1;task.save();changed.append(task.id)
    if changed:record_change(order.id,tuple(changed),actor_id,timezone.now(),eligibility)
    return tuple(task_view(t) for t in order.tasks.select_related("order__customer"))

@transaction.atomic
def move_task(task_id,target_on,actor_id,expected_version):
    original=Task.objects.get(pk=task_id)
    Order.objects.select_for_update().get(pk=original.order_id)
    task=Task.objects.select_for_update().select_related("order__customer").get(pk=task_id);check_version(task,expected_version)
    if task.state in ("done","cancelled"):raise ValidationError("완료·취소 업무는 먼저 재작업 여부를 확인하세요.")
    if target_on and target_on.weekday()>=5:raise ValidationError("사내 업무일은 평일로 지정하세요.")
    old_on=task.effective_on
    task.manual_on=target_on;task.recalc_needed=False
    task.suspended=task.auto_on is None
    task.effective_on=None if task.suspended else (target_on or task.auto_on)
    task.row_version+=1
    if old_on!=task.effective_on:task.notice_revision+=1
    task.save()
    audit(task.order,actor_id,"move_task",task.id,{"effective_on":old_on},{"effective_on":task.effective_on,"manual_on":target_on})
    candidate=_eligible(task,old_on,task.state)
    record_change(task.order_id,(task.id,),actor_id,timezone.now(),[candidate] if candidate else [])
    return task_view(task)

@transaction.atomic
def set_substep(substep_id,done,actor_id,expected_version):
    original=Substep.objects.select_related("task").get(pk=substep_id)
    Order.objects.select_for_update().get(pk=original.task.order_id)
    task=Task.objects.select_for_update().select_related("order__customer").get(pk=original.task_id);check_version(task,expected_version)
    if task.state=="cancelled":raise ValidationError("취소된 업무입니다.")
    step=Substep.objects.get(pk=substep_id)
    if step.done==bool(done):return task_view(task)
    if task.state=='done':raise ValidationError('완료 업무는 재작업 필요를 선택한 뒤 체크를 변경하세요. 이전 완료 기록을 보존합니다.')
    old_state=task.state;step.done=bool(done);step.completed_at=timezone.now() if done else None;step.completed_by_id=actor_id if done else None;step.save()
    count=task.substeps.count();completed=task.substeps.filter(done=True).count()
    task.state="done" if completed==count else ("partial" if completed else "open")
    task.completed_at=timezone.now() if task.state=="done" else None;task.completed_by_id=actor_id if task.state=="done" else None
    task.row_version+=1;task.notice_revision+=1;task.save()
    audit(task.order,actor_id,"check_substep",step.id,{"done":not bool(done)},{"done":bool(done),"state":task.state})
    candidate=_eligible(task,task.effective_on,old_state)
    record_change(task.order_id,(task.id,),actor_id,timezone.now(),[candidate] if candidate else [])
    return task_view(task)

@transaction.atomic
def review_completed_task(task_id,reopen,actor_id,expected_version):
    original=Task.objects.get(pk=task_id);Order.objects.select_for_update().get(pk=original.order_id)
    task=Task.objects.select_for_update().select_related("order__customer").get(pk=task_id);check_version(task,expected_version)
    if task.state!="done":raise ValidationError("완료한 업무의 재확인을 선택하세요.")
    before={"state":task.state,"completed_at":task.completed_at,"completed_by":task.completed_by_id,"steps":list(task.substeps.values("id","label","done","completed_at","completed_by_id"))}
    if reopen:
        spec=next((s for s in build_task_specs(snapshot(task.order)) if s.kind==task.kind and s.shipment_id==task.shipment_id),None)
        if task.order.cancelled or spec is None:raise ValidationError('취소된 PO·회차의 완료 업무는 재작업으로 전환할 수 없습니다.')
        for i,label in enumerate(spec.substeps):
            Substep.objects.update_or_create(task=task,position=i,defaults={'label':label})
        task.substeps.update(done=False,completed_at=None,completed_by=None)
        task.state="open";task.completed_at=None;task.completed_by=None
        task.suspended=task.auto_on is None
        task.effective_on=None if task.suspended else (task.manual_on or task.auto_on)
        task.notice_revision+=1
    task.needs_review=False;task.row_version+=1;task.save()
    audit(task.order,actor_id,"reopen_task" if reopen else "review_task",task.id,before,{"state":task.state})
    candidate=_eligible(task,None,"done") if reopen else None
    record_change(task.order_id,(task.id,),actor_id,timezone.now(),[candidate] if candidate else [])
    return task_view(task)

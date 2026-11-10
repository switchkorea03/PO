from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from common.errors import ValidationError, VersionConflict, AllocationExceeded, AlreadyShipped
from common.audit import audit
from common.events import record_change
from .models import Customer, Order, OrderLine, Shipment, ShipmentLine

def decimal_value(value, *, positive=False):
    try: result=Decimal(str(value))
    except (InvalidOperation,ValueError,TypeError): raise ValidationError("수량·금액을 확인하세요.")
    if not result.is_finite() or (positive and result<=0): raise ValidationError("유효한 양수 수량을 입력하세요.")
    if result.as_tuple().exponent < -10 or result.adjusted() >= 20: raise ValidationError("지원 정밀도를 초과합니다. 관리자에게 정밀도 확대를 요청하세요.")
    return result

def check_version(obj, expected):
    if expected is None or obj.row_version != int(expected): raise VersionConflict("다른 사용자가 수정했습니다. 새로고침 후 다시 확인하세요.")

def _lock_order(order_id):
    return Order.objects.select_for_update().get(pk=order_id,is_deleted=False)

def _changed(order,actor_id,action,target,before=None,after=None,reason=""):
    order.row_version+=1;order.save(update_fields=["row_version","updated_at"])
    audit(order,actor_id,action,target,before,after,reason)
    from work.services import reconcile_order
    reconcile_order(order.id,actor_id)

def _valid_order(data):
    if data.order_type not in ("domestic","overseas") or data.erp_type not in ("domestic","export","unspecified"): raise ValidationError("거래 구분을 확인하세요.")
    if not data.po_number.strip() or len(data.po_number)>120 or not data.lines: raise ValidationError("PO 번호와 품목이 필요합니다.")
    if not Customer.objects.filter(pk=data.customer_id).exists(): raise ValidationError("고객을 선택하세요.")
    if data.order_type=="overseas" and not data.received_on: raise ValidationError("해외 PO 실제 수령일을 확인하세요.")
    for line in data.lines:
        if not (line.code.strip() or line.name.strip()) or not line.unit.strip() or len(line.currency)!=3: raise ValidationError("품목·단위·통화를 확인하세요.")
        decimal_value(line.quantity,positive=True)
        if line.unit_price is not None:
            if decimal_value(line.unit_price)<0: raise ValidationError("단가는 음수일 수 없습니다.")
        if data.order_type=="domestic" and not line.requested_due: raise ValidationError("국내 요청납기를 입력하세요.")

def _order_snapshot(order):
    fields=('customer_id','po_number','order_type','erp_type','ordered_on','received_on','contact','note','cancelled')
    result={field:getattr(order,field) for field in fields}
    result['lines']=list(order.lines.order_by('id').values('id','code','name','quantity','unit','unit_price','currency','source_amount','requested_due','cancelled_quantity','internal_name'))
    return result

@transaction.atomic
def save_order(data,actor_id,expected_version,order_id=None):
    _valid_order(data)
    before={}
    if order_id:
        order=_lock_order(order_id);check_version(order,expected_version)
        before=_order_snapshot(order)
        if order.cancelled:raise ValidationError("취소된 PO는 수정할 수 없습니다.")
        if order.shipments.exists() and data.order_type!=order.order_type:raise ValidationError("회차가 있는 PO의 국내외 구분은 변경할 수 없습니다.")
        if data.customer_id!=order.customer_id:raise ValidationError("수정본의 고객을 바꿀 수 없습니다. 새 PO로 등록하세요.")
    else:
        Customer.objects.select_for_update().get(pk=data.customer_id)
        if Order.objects.filter(customer_id=data.customer_id,po_number=data.po_number.strip()).exists():raise ValidationError("같은 고객·PO 번호가 있습니다. 수정본으로 비교하세요.")
        order=Order.objects.create(customer_id=data.customer_id,po_number=data.po_number.strip(),order_type=data.order_type)
    if Order.objects.exclude(pk=order.id).filter(customer_id=data.customer_id,po_number=data.po_number.strip()).exists():raise ValidationError("같은 고객·PO 번호가 이미 있습니다.")
    old={str(v.id):v for v in order.lines.select_for_update().all()};seen=set();due_changed=[]
    for field in ["customer_id","po_number","order_type","erp_type","ordered_on","received_on","contact","note"]:setattr(order,field,getattr(data,field))
    order.po_number=order.po_number.strip();order.save()
    for item in data.lines:
        key=str(item.id) if item.id else None
        if key and (key not in old or key in seen):raise ValidationError("품목 식별자가 잘못되었거나 중복되었습니다.")
        line=old[key] if key else OrderLine(order=order)
        changed_due=bool(order_id and key in old and line.requested_due!=item.requested_due)
        qty=decimal_value(item.quantity,positive=True)
        if line.pk and key in old and (qty < line.allocated+line.cancelled_quantity or qty<line.shipped+line.cancelled_quantity):raise AllocationExceeded("기존 회차·출고·취소 수량보다 주문수량을 줄일 수 없습니다.")
        for field in ["code","name","unit","currency","requested_due","source_amount"]:setattr(line,field,getattr(item,field))
        from .item_mapping import mapped_internal_name
        line.internal_name=item.internal_name or mapped_internal_name(item.code,item.name)
        line.quantity=qty;line.unit_price=decimal_value(item.unit_price) if item.unit_price is not None else None
        line.full_clean();line.save();seen.add(str(line.id))
        if changed_due:due_changed.append(line)
    for key,line in old.items():
        if key not in seen:
            if line.allocations.exists():raise ValidationError("회차에 연결된 품목은 삭제하지 말고 수량을 조정하세요.")
            line.delete()
    for line in due_changed:_reschedule_due_line(order,line)
    if not order_id:
        from work.rules import next_weekday
        grouped=defaultdict(list)
        for line in order.lines.all():grouped[line.requested_due if order.order_type=="domestic" else None].append(line)
        for sequence,(due,lines) in enumerate(sorted(grouped.items(),key=lambda x:str(x[0])),1):
            shipment=Shipment.objects.create(order=order,sequence=sequence,ship_on=next_weekday(due) if due else None)
            ShipmentLine.objects.bulk_create([ShipmentLine(shipment=shipment,line=line,quantity=line.quantity) for line in lines])
    _changed(order,actor_id,"save_order",order.id,before,_order_snapshot(order))
    return order

@transaction.atomic
def delete_order(order_id,actor_id,expected_version):
    order=Order.objects.select_for_update().get(pk=order_id)
    check_version(order,expected_version)
    if not order.is_deleted:
        order.is_deleted=True;order.deleted_at=timezone.now();order.row_version+=1
        order.save(update_fields=['is_deleted','deleted_at','row_version','updated_at'])
        audit(order,actor_id,'delete_order',order.id,{'is_deleted':False},{'is_deleted':True})
    return order

@transaction.atomic
def restore_order(order_id,actor_id,expected_version):
    order=Order.objects.select_for_update().get(pk=order_id)
    check_version(order,expected_version)
    if order.is_deleted:
        order.is_deleted=False;order.deleted_at=None;order.row_version+=1
        order.save(update_fields=['is_deleted','deleted_at','row_version','updated_at'])
        audit(order,actor_id,'restore_order',order.id,{'is_deleted':True},{'is_deleted':False})
    return order

@transaction.atomic
def reregister_order(order_id,data,actor_id,expected_version):
    # Restoration and edited values either both succeed or both roll back.
    order=Order.objects.select_for_update().get(pk=order_id)
    check_version(order,expected_version)
    before={'is_deleted':order.is_deleted,'cancelled':order.cancelled}
    if not (order.is_deleted or order.cancelled):raise ValidationError('이미 등록된 PO입니다. 새로고침 후 확인하세요.')
    if order.is_deleted:order=restore_order(order.id,actor_id,order.row_version)
    if order.cancelled:
        order.cancelled=False;order.row_version+=1
        order.save(update_fields=['cancelled','row_version','updated_at'])
    order=save_order(data,actor_id,order.row_version,order.id)
    created=[]
    if before['cancelled']:
        # Keep cancelled/completed shipment history and plan only unallocated
        # remaining quantities as new shipments, without duplicating actuals.
        from work.rules import next_weekday
        grouped=defaultdict(list)
        for line in order.lines.all():
            quantity=line.quantity-line.cancelled_quantity-line.allocated
            if quantity>0:grouped[line.requested_due if order.order_type=='domestic' else None].append((line,quantity))
        sequence=(order.shipments.aggregate(v=Max('sequence'))['v'] or 0)+1
        for number,(due,items) in enumerate(sorted(grouped.items(),key=lambda value:str(value[0])),sequence):
            shipment=Shipment.objects.create(order=order,sequence=number,ship_on=next_weekday(due) if due else None)
            ShipmentLine.objects.bulk_create([ShipmentLine(shipment=shipment,line=line,quantity=quantity) for line,quantity in items])
            created.append(str(shipment.id))
        from work.services import reconcile_order
        reconcile_order(order.id,actor_id,reopen_cancelled=True)
    audit(order,actor_id,'reregister_order',order.id,before,
          {'is_deleted':False,'cancelled':False,'new_shipments':created})
    return order

def _validate_allocations(order,allocations,shipment=None):
    if not allocations:raise ValidationError("회차 품목과 수량을 입력하세요.")
    lines={v.id:v for v in order.lines.select_for_update().order_by("id")};validated={}
    for key,value in allocations.items():
        from uuid import UUID
        key=UUID(str(key))
        if key not in lines:raise ValidationError("다른 PO의 품목을 배정할 수 없습니다.")
        qty=decimal_value(value,positive=True);line=lines[key]
        other=line.allocations.filter(shipment__cancelled=False)
        if shipment:other=other.exclude(shipment=shipment)
        allocated=sum((v.quantity for v in other),Decimal(0))
        if allocated+qty+line.cancelled_quantity>line.quantity:raise AllocationExceeded("회차 배정 합계가 주문수량을 초과합니다.")
        validated[key]=qty
    return validated

@transaction.atomic
def save_shipment(order_id,data,actor_id,expected_version):
    order=_lock_order(order_id)
    if order.cancelled:raise ValidationError("취소된 PO입니다.")
    if data.id:
        shipment=Shipment.objects.select_for_update().get(pk=data.id,order=order);check_version(shipment,expected_version)
        if shipment.completed:raise AlreadyShipped("출고 완료 건은 정정으로 변경하세요.")
        if shipment.cancelled:raise ValidationError("취소된 회차입니다.")
    else:shipment=None
    if order.order_type=="domestic" and (not data.ship_on or data.ship_on.weekday()>=5):raise ValidationError("국내 출고일은 평일로 지정하세요.")
    allocations=_validate_allocations(order,data.allocations,shipment)
    if not shipment:
        sequence=(order.shipments.aggregate(v=Max("sequence"))["v"] or 0)+1
        shipment=Shipment.objects.create(order=order,sequence=sequence)
    before={"ship_on":shipment.ship_on,"etd":shipment.etd,"eta":shipment.eta,"allocations":{str(v.line_id):str(v.quantity) for v in shipment.allocations.all()}}
    shipment.ship_on=data.ship_on if order.order_type=="domestic" else None
    shipment.etd=data.etd if order.order_type=="overseas" else None;shipment.eta=data.eta
    shipment.row_version+=1;shipment.save()
    shipment.allocations.all().delete()
    ShipmentLine.objects.bulk_create([ShipmentLine(shipment=shipment,line_id=key,quantity=qty) for key,qty in allocations.items()])
    _changed(order,actor_id,"save_shipment",shipment.id,before,{"ship_on":shipment.ship_on,"etd":shipment.etd,"eta":shipment.eta,"allocations":{str(k):str(v) for k,v in allocations.items()}})
    return shipment

@transaction.atomic
def confirm_shipment(shipment_id,actor_id,expected_version):
    original=Shipment.objects.get(pk=shipment_id);order=_lock_order(original.order_id)
    shipment=Shipment.objects.select_for_update().get(pk=shipment_id)
    if shipment.completed:return shipment
    check_version(shipment,expected_version)
    if shipment.cancelled or order.cancelled:raise ValidationError("취소된 회차입니다.")
    if order.order_type=="overseas" and not shipment.etd:raise ValidationError("선적 완료 전 ETD를 입력하세요.")
    _validate_allocations(order,{v.line_id:v.quantity for v in shipment.allocations.all()},shipment)
    shipment.completed=True;shipment.completed_at=timezone.now();shipment.completed_by_id=actor_id;shipment.row_version+=1;shipment.save()
    _changed(order,actor_id,"confirm_shipment",shipment.id,after={"completed":True})
    return shipment

@transaction.atomic
def cancel_remaining(line_id,quantity,actor_id,expected_version):
    original=OrderLine.objects.get(pk=line_id);order=_lock_order(original.order_id);check_version(order,expected_version)
    line=OrderLine.objects.select_for_update().get(pk=line_id);qty=decimal_value(quantity,positive=True)
    if qty>line.quantity-line.allocated-line.cancelled_quantity:raise AllocationExceeded("미완료 회차 배정을 먼저 줄인 후 미배정 잔량을 취소하세요.")
    before=line.cancelled_quantity;line.cancelled_quantity+=qty;line.save()
    _changed(order,actor_id,"cancel_remaining",line.id,{"cancelled":before},{"cancelled":line.cancelled_quantity})
    return line

@transaction.atomic
def correct_shipment(shipment_id,allocations,reason,actor_id,expected_version):
    original=Shipment.objects.get(pk=shipment_id);order=_lock_order(original.order_id)
    shipment=Shipment.objects.select_for_update().get(pk=shipment_id);check_version(shipment,expected_version)
    if not shipment.completed or not reason.strip():raise ValidationError("완료 실적 정정에는 사유가 필요합니다.")
    validated=_validate_allocations(order,allocations,shipment)
    before={str(v.line_id):str(v.quantity) for v in shipment.allocations.all()}
    shipment.allocations.all().delete()
    ShipmentLine.objects.bulk_create([ShipmentLine(shipment=shipment,line_id=key,quantity=qty) for key,qty in validated.items()])
    shipment.row_version+=1;shipment.save()
    _changed(order,actor_id,"correct_shipment",shipment.id,before,{str(k):str(v) for k,v in validated.items()},reason)
    return shipment

def _reschedule_due_line(order,line):
    if order.order_type!='domestic':return
    from work.rules import next_weekday
    ship_on=next_weekday(line.requested_due)
    def new_shipment():
        sequence=(order.shipments.aggregate(v=Max('sequence'))['v'] or 0)+1
        return Shipment.objects.create(order=order,sequence=sequence,ship_on=ship_on)
    pending=list(line.allocations.select_related('shipment').filter(shipment__completed=False,shipment__cancelled=False))
    for allocation in pending:
        shipment=allocation.shipment
        if shipment.ship_on==ship_on:continue
        if shipment.allocations.count()==1:
            shipment.ship_on=ship_on
        else:
            allocation.shipment=new_shipment();allocation.save(update_fields=['shipment'])
        shipment.row_version+=1;shipment.save(update_fields=['ship_on','row_version'])
    unallocated=line.quantity-line.cancelled_quantity-line.allocated
    if unallocated>0:ShipmentLine.objects.create(shipment=new_shipment(),line=line,quantity=unallocated)

@transaction.atomic
def update_requested_due(line_id,requested_due,actor_id,expected_version):
    original=OrderLine.objects.get(pk=line_id)
    order=_lock_order(original.order_id);check_version(order,expected_version)
    if order.cancelled:raise ValidationError('취소된 PO는 재등록한 뒤 납기일을 수정하세요.')
    if order.order_type=='domestic' and requested_due is None:raise ValidationError('국내 PO의 납기일을 입력하세요.')
    line=OrderLine.objects.select_for_update().get(pk=line_id)
    before={'requested_due':line.requested_due,'shipments':list(line.allocations.values('shipment_id','shipment__ship_on'))}
    if line.requested_due==requested_due:return order
    line.requested_due=requested_due;line.save(update_fields=['requested_due'])
    _reschedule_due_line(order,line)
    after={'requested_due':requested_due,'shipments':list(line.allocations.values('shipment_id','shipment__ship_on'))}
    _changed(order,actor_id,'update_requested_due',line.id,before,after)
    return order

@transaction.atomic
def cancel_order(order_id,actor_id,expected_version):
    order=_lock_order(order_id);check_version(order,expected_version)
    order.cancelled=True;order.save()
    for shipment in order.shipments.filter(completed=False):
        shipment.cancelled=True;shipment.row_version+=1;shipment.save()
    _changed(order,actor_id,"cancel_order",order.id,after={"cancelled":True})
    return order

@transaction.atomic
def cancel_shipment(shipment_id,reason,actor_id,expected_version):
    original=Shipment.objects.get(pk=shipment_id);order=_lock_order(original.order_id)
    shipment=Shipment.objects.select_for_update().get(pk=shipment_id);check_version(shipment,expected_version)
    if shipment.completed or shipment.cancelled or order.cancelled:raise ValidationError('미완료 회차만 취소할 수 있습니다.')
    if not reason.strip():raise ValidationError('회차 취소 사유를 입력하세요.')
    shipment.cancelled=True;shipment.row_version+=1;shipment.save()
    _changed(order,actor_id,'cancel_shipment',shipment.id,{'cancelled':False},{'cancelled':True,'allocations':{str(a.line_id):str(a.quantity) for a in shipment.allocations.all()}},reason)
    return shipment

@transaction.atomic
def update_eta(shipment_id,eta,actor_id,expected_version):
    original=Shipment.objects.get(pk=shipment_id);order=_lock_order(original.order_id)
    shipment=Shipment.objects.select_for_update().get(pk=shipment_id);check_version(shipment,expected_version)
    if order.order_type!='overseas' or order.cancelled or shipment.cancelled:raise ValidationError('유효한 해외 선적회차를 선택하세요.')
    before=shipment.eta;shipment.eta=eta;shipment.row_version+=1;shipment.save()
    _changed(order,actor_id,'update_eta',shipment.id,{'eta':before},{'eta':eta})
    return shipment

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
    return Order.objects.select_for_update().get(pk=order_id)

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
    result['lines']=list(order.lines.order_by('id').values('id','code','name','quantity','unit','unit_price','currency','source_amount','requested_due','cancelled_quantity'))
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
    old={str(v.id):v for v in order.lines.select_for_update().all()};seen=set()
    for field in ["customer_id","po_number","order_type","erp_type","ordered_on","received_on","contact","note"]:setattr(order,field,getattr(data,field))
    order.po_number=order.po_number.strip();order.save()
    for item in data.lines:
        key=str(item.id) if item.id else None
        if key and (key not in old or key in seen):raise ValidationError("품목 식별자가 잘못되었거나 중복되었습니다.")
        line=old[key] if key else OrderLine(order=order)
        qty=decimal_value(item.quantity,positive=True)
        if line.pk and key in old and (qty < line.allocated+line.cancelled_quantity or qty<line.shipped+line.cancelled_quantity):raise AllocationExceeded("기존 회차·출고·취소 수량보다 주문수량을 줄일 수 없습니다.")
        for field in ["code","name","unit","currency","requested_due","source_amount"]:setattr(line,field,getattr(item,field))
        line.quantity=qty;line.unit_price=decimal_value(item.unit_price) if item.unit_price is not None else None
        line.full_clean();line.save();seen.add(str(line.id))
    for key,line in old.items():
        if key not in seen:
            if line.allocations.exists():raise ValidationError("회차에 연결된 품목은 삭제하지 말고 수량을 조정하세요.")
            line.delete()
    if not order_id:
        from work.rules import next_weekday
        grouped=defaultdict(list)
        for line in order.lines.all():grouped[line.requested_due if order.order_type=="domestic" else None].append(line)
        for sequence,(due,lines) in enumerate(sorted(grouped.items(),key=lambda x:str(x[0])),1):
            shipment=Shipment.objects.create(order=order,sequence=sequence,ship_on=next_weekday(due) if due else None)
            ShipmentLine.objects.bulk_create([ShipmentLine(shipment=shipment,line=line,quantity=line.quantity) for line in lines])
    _changed(order,actor_id,"save_order",order.id,before,_order_snapshot(order))
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

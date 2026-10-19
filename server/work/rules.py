from datetime import timedelta
from common.contracts import TaskSpec,TaskKind
from .catalog import catalog

def next_weekday(value):
    while value.weekday()>=5:value+=timedelta(days=1)
    return value

def previous_weekday(value):
    value-=timedelta(days=1)
    while value.weekday()>=5:value-=timedelta(days=1)
    return value

def next_week_tuesday(value):return value+timedelta(days=8-value.weekday())

def build_task_specs(order):
    result=[]
    def append(kind,shipment_id,basis,auto,currency=None):
        title,steps=catalog(kind,order.erp_type,currency or order.currency)
        result.append(TaskSpec(order.id,shipment_id,TaskKind(kind),basis,auto,title,steps))
    if order.order_type=="domestic":
        for shipment in order.shipments:
            for kind in ("domestic_share","domestic_request","domestic_statement","domestic_excel","domestic_voucher"):
                auto=(previous_weekday(shipment.ship_on) if kind in ("domestic_share","domestic_request") else shipment.ship_on) if shipment.ship_on else None
                currencies={line.currency for line in order.lines if line.id in shipment.allocations}
                append(kind,shipment.id,shipment.ship_on,auto,next(iter(currencies)) if len(currencies)==1 else "MIX")
    else:
        received=order.received_on
        append("overseas_invoice",None,received,next_weekday(received) if received else None)
        append("overseas_bl_eta",None,received,next_week_tuesday(received) if received else None)
        for shipment in order.shipments:
            for kind in ("overseas_erp","overseas_mail","overseas_excel"):
                append(kind,shipment.id,shipment.etd,next_weekday(shipment.etd+timedelta(days=1)) if shipment.etd else None)
    return tuple(result)

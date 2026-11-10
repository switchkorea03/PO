from uuid import UUID
from decimal import Decimal
from common.contracts import OrderInput,LineInput,ShipmentInput
from common.http import parse_date

def order_input(data):
    lines=tuple(LineInput(
        UUID(line['id']) if line.get('id') else None,
        line.get('code',''),line.get('name',''),Decimal(str(line['quantity'])),line.get('unit',''),
        Decimal(str(line['unit_price'])) if line.get('unit_price') not in (None,'') else None,
        line.get('currency','KRW'),
        Decimal(str(line['source_amount'])) if line.get('source_amount') not in (None,'') else None,
        parse_date(line.get('requested_due')),line.get('internal_name','')
    ) for line in data.get('lines',[]))
    return OrderInput(UUID(data['customer_id']),data['po_number'],data['order_type'],
        data.get('erp_type','unspecified'),parse_date(data.get('ordered_on')),parse_date(data.get('received_on')),
        data.get('contact',''),data.get('note',''),lines)

def shipment_input(data):
    return ShipmentInput(UUID(data["id"]) if data.get("id") else None,parse_date(data.get("ship_on")),parse_date(data.get("etd")),parse_date(data.get("eta")),{UUID(k):Decimal(str(v)) for k,v in data.get("allocations",{}).items() if str(v).strip() and Decimal(str(v))!=0})

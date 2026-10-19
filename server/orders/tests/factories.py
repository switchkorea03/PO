from datetime import date
from decimal import Decimal
from uuid import uuid4
from django.contrib.auth import get_user_model
from orders.models import Customer, Order, OrderLine

def make_order(order_type="domestic",quantities=("100",),dues=("2026-10-19",),received_on="2026-10-18"):
    customer=Customer.objects.create(name="범진전자-"+uuid4().hex[:8],default_type=order_type)
    order=Order.objects.create(customer=customer,po_number="PO-"+str(Customer.objects.count()),order_type=order_type,received_on=date.fromisoformat(received_on) if received_on else None)
    for n,q in enumerate(quantities):
        OrderLine.objects.create(order=order,code=f"ITEM-{n}",name=f"품목{n}",quantity=Decimal(q),unit="EA",unit_price=Decimal("0.2"),currency="KRW",requested_due=date.fromisoformat(dues[min(n,len(dues)-1)]) if dues else None)
    return order

def make_shipment(order,quantity,ship_on=None,etd=None):
    from orders.services import save_shipment
    from common.contracts import ShipmentInput
    user=get_user_model().objects.first() or get_user_model().objects.create_user("fixture")
    return save_shipment(order.id,ShipmentInput(None,date.fromisoformat(ship_on) if ship_on else None,date.fromisoformat(etd) if etd else None,None,{order.lines.first().id:Decimal(quantity)}),user.id,None)

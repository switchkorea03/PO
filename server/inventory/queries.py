from decimal import Decimal,localcontext
from orders.models import OrderLine
from orders.item_mapping import INTERNAL_NAMES,SPEC_ALIASES,ITEM_MAPPING
from .providers import get_inventory_provider


def inventory_rows(query=''):
    grouped={}
    lines=OrderLine.objects.filter(order__cancelled=False,order__is_deleted=False).select_related('order__customer').prefetch_related('allocations__shipment')
    with localcontext() as context:
        context.prec=65
        for line in lines:
            name=line.resolved_internal_name.strip().upper()
            if not name:continue
            unit=line.unit.strip().upper()
            key=(name,unit)
            row=grouped.setdefault(key,{'item_name':name,'unit':unit,'remaining':Decimal('0'),'orders':{},'search':set()})
            shipped=sum((allocation.quantity for allocation in line.allocations.all() if allocation.shipment.completed and not allocation.shipment.cancelled),Decimal('0'))
            remaining=max(Decimal('0'),line.quantity-line.cancelled_quantity-shipped)
            row['remaining']+=remaining
            if remaining:row['orders'][line.order_id]={'id':line.order_id,'po_number':line.order.po_number}
            row['search'].update([name,line.code,line.name,line.order.customer.name,line.order.po_number])
    known_names={name for name,unit in grouped}
    for name in dict.fromkeys((*INTERNAL_NAMES,*SPEC_ALIASES.values())):
        if name not in known_names:grouped[(name,'')]={'item_name':name,'unit':'','remaining':Decimal('0'),'orders':{},'search':{name}}
    for row in grouped.values():
        row['search'].update(token for token,target in {**ITEM_MAPPING,**SPEC_ALIASES}.items() if target==row['item_name'])
    needle=query.strip().casefold()
    rows=[row for row in grouped.values() if not needle or any(needle in value.casefold() for value in row['search'])]
    snapshots=get_inventory_provider().fetch([(row['item_name'],row['unit']) for row in rows])
    for row in rows:
        row['stock']=snapshots[(row['item_name'],row['unit'])]
        row['orders']=list(row['orders'].values());row['order_count']=len(row['orders']);row.pop('search')
    return sorted(rows,key=lambda row:(row['remaining']==0,row['item_name'],row['unit']))

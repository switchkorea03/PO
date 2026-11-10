from decimal import Decimal, InvalidOperation
from django import template
from django.utils.html import json_script

register = template.Library()

@register.simple_tag
def item_mapping_json():
    from orders.item_mapping import ITEM_MAPPING
    return json_script(ITEM_MAPPING,element_id='item-mapping-data')

@register.simple_tag
def internal_names_json():
    from orders.item_mapping import INTERNAL_NAMES
    return json_script(INTERNAL_NAMES,element_id='internal-names-data')

@register.simple_tag
def spec_aliases_json():
    from orders.item_mapping import SPEC_ALIASES
    return json_script(SPEC_ALIASES,element_id='spec-aliases-data')

@register.filter
def po_number(value):
    """Group thousands without converting precise quantities/money to floats."""
    if value is None or value == '':
        return '—'
    try:
        number = Decimal(str(value))
        if not number.is_finite():return '—'
        result = format(number, ',f')
        return result.rstrip('0').rstrip('.') if '.' in result else result
    except (InvalidOperation, ValueError, TypeError):
        return '—'

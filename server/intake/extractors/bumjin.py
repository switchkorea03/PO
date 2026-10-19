"""BUMJIN's two-level material/specification PDF table (text extraction order)."""
import re
from datetime import date
from .base import ExtractedField,ExtractionResult

def compact(text):
    return re.sub(r'[^a-z0-9]','',text.lower())

def iso_date(text):
    match=re.fullmatch(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})',text.strip())
    if match:
        try:return date(*(int(part) for part in match.groups())).isoformat()
        except ValueError:pass
    return None

NUMBER=r'\d[\d,]*(?:\.\d+)?'
ITEM=re.compile(r'^\s*\d{1,6}\s+(?P<code>\S+)\s+(?P<name>.+?)\s+(?P<quantity>'+NUMBER+r')\s+(?P<unit>[A-Za-z]+)\s+(?P<unit_price>'+NUMBER+r')\s+(?P<source_amount>'+NUMBER+r')\s*$')
HEADER='itemmaterialoldmaterialmaterialdescriptionquantityunitpriceamount'
SUBHEADER='customercodespecificationdeliverydate'

def extract_bumjin(evidence):
    pdf=[entry for entry in evidence if entry.page is not None and entry.cell is None]
    if not any('bumjinelectronicscoltd' in compact(entry.text) for entry in pdf):return None
    if not any(compact(entry.text)==HEADER for entry in pdf):return None
    if not any(compact(entry.text)==SUBHEADER for entry in pdf):return None
    fields={key:ExtractedField(None) for key in ('po_number','customer_name','ordered_on','received_on','contact','etd')}
    currency=None;currency_evidence=()
    for entry in pdf:
        text=entry.text.strip()
        for pattern,key in ((r'PO\s*no\.?\s*[:：]?\s+(.+)','po_number'),(r'Po\s+Date\s*[:：]?\s+(.+)','ordered_on'),(r'Charger\s*[:：]?\s+(.+)','contact')):
            match=re.fullmatch(pattern,text,re.I)
            if match:
                value=match.group(1).strip()
                fields[key]=ExtractedField(iso_date(value) if key=='ordered_on' else value,(entry,))
        # Buyer, rather than End Customer or Vendor, is the PO customer.
        if re.match(r'^BUMJIN\s+ELECTRONICS\s+CO\s*\.?\s*,?\s*LTD\b',text,re.I):
            fields['customer_name']=ExtractedField('범진전자',(entry,))
        match=re.fullmatch(r'CUR\s+([A-Z]{3})',text)
        if match:currency=match.group(1);currency_evidence=(entry,)
    lines=[];active=False;current=None;page=None;after_due=False
    for entry in pdf:
        if entry.page!=page:active=False;current=None;page=entry.page
        text=entry.text.strip()
        if compact(text)==SUBHEADER:active=True;current=None;continue
        if re.match(r'^Total\s+Items\b',text,re.I):active=False;current=None;continue
        if not active:continue
        match=ITEM.fullmatch(text)
        if match:
            current={key:ExtractedField(None) for key in ('code','name','quantity','unit','unit_price','currency','source_amount','requested_due')}
            for key,value in match.groupdict().items():
                current[key]=ExtractedField(value.replace(',','') if key in ('quantity','unit_price','source_amount') else value,(entry,))
            current['currency']=ExtractedField(currency,currency_evidence)
            lines.append(current);after_due=False
        elif current is not None:
            due=iso_date(text)
            if due:
                current['requested_due']=ExtractedField(due,(entry,));after_due=True
            elif not after_due:
                field=current['name']
                current['name']=ExtractedField(field.value+' / '+text,field.evidence+(entry,))
    warnings=['범진전자 양식: Buyer를 고객으로 연결했습니다. 품목·규격·납기를 원본과 비교한 후 확정하세요.']
    if not lines:warnings.append('품목 표를 판독하지 못했습니다. 수동입력으로 등록하세요.')
    if any(line['requested_due'].value is None for line in lines):warnings.append('납기 미인식 품목이 있습니다. 원본을 확인하여 입력하세요.')
    return ExtractionResult(fields,tuple(lines),tuple(warnings),'review',tuple(evidence))

"""CHEMTROVINA purchase orders with multi-line description/quantity cells."""
import re
from decimal import Decimal,localcontext
from .base import ExtractedField,ExtractionResult
from .bumjin import iso_date

NUMBER=r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
ITEM=re.compile(r'^\s*\d{1,6}\s+([A-Z][A-Z0-9._/-]*)\s+(.+)$')
TAIL=re.compile(r'(?P<quantity>'+NUMBER+r')\s+(?P<unit>[A-Za-z]{1,8})\s+(?P<unit_price>'+NUMBER+r')\s+(?P<source_amount>'+NUMBER+r')\s+(?P<requested_due>\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s*$')


def extract_chemtrovina(evidence):
    entries=[entry for entry in evidence if entry.page is not None and entry.cell is None]
    buyer=[];in_buyer=False
    for entry in entries:
        text=entry.text.strip()
        if re.fullmatch(r'Buyer\s+Detail',text,re.I):in_buyer=True
        elif re.fullmatch(r'Supplier\s+Detail',text,re.I):in_buyer=False
        elif in_buyer:buyer.append(entry)
    identity=next((entry for entry in buyer if 'CHEMTROVINA' in entry.text.upper()),None)
    if identity is None or not any(re.search(r'Purchase\s+Order',entry.text,re.I) for entry in entries):return None
    fields={key:ExtractedField(None) for key in ('po_number','customer_name','ordered_on','received_on','contact','etd')}
    fields['customer_name']=ExtractedField('켐트로비나',(identity,))
    fields['order_type']=ExtractedField('overseas',(identity,))
    currency=None;currency_evidence=();total=None
    for entry in entries:
        text=entry.text.strip()
        match=re.fullmatch(r'PO\s*(?:No\.?|Number)\s*[:：]?\s+(\S+)',text,re.I)
        if match:fields['po_number']=ExtractedField(match.group(1),(entry,))
        match=re.fullmatch(r'PO\s*Date\s*[:：]?\s+(.+)',text,re.I)
        if match:fields['ordered_on']=ExtractedField(iso_date(match.group(1)),(entry,))
        match=re.fullmatch(r'Amount\s+([A-Z]{3})\s+('+NUMBER+r')',text,re.I)
        if match:
            currency=match.group(1).upper();currency_evidence=(entry,)
            total=Decimal(match.group(2).replace(',',''))
    for entry in buyer:
        match=re.fullmatch(r'In\s+Charge\s*[:：]?\s+(.+)',entry.text.strip(),re.I)
        if match:fields['contact']=ExtractedField(match.group(1),(entry,))
    lines=[];warnings=['켐트로비나 양식: Buyer를 고객으로 연결했습니다. 인식값을 원본과 비교한 후 확정하세요.']
    current=None
    def flush():
        if current is None:return
        code,pieces=current;body=' '.join(text for text,_ in pieces);proof=tuple(entry for _,entry in pieces)
        line={key:ExtractedField(None) for key in ('code','name','quantity','unit','unit_price','currency','source_amount','requested_due')}
        line['code']=ExtractedField(code,(proof[0],));line['currency']=ExtractedField(currency,currency_evidence)
        match=TAIL.search(body)
        if match:
            for key,value in match.groupdict().items():
                if key in ('quantity','unit_price','source_amount'):value=value.replace(',','')
                if key=='requested_due':value=iso_date(value)
                line[key]=ExtractedField(value,proof)
            description=body[:match.start()].strip()
        else:
            description=body;warnings.append(f'{code}: 수량·단가·금액·납기 미인식. 원본을 확인하여 입력하세요.')
        line['name']=ExtractedField(description,proof)
        from orders.item_mapping import mapped_internal_name
        internal=mapped_internal_name(code,description)
        if internal:line['internal_name']=ExtractedField(internal,proof)
        lines.append(line)
    page=None
    for entry in entries:
        if page is not None and entry.page!=page:flush();current=None
        page=entry.page;text=entry.text.strip()
        if re.match(r'^(?:[A-Z]{3}\s+)?Total\s+Amount\b',text,re.I):flush();current=None;continue
        match=ITEM.fullmatch(text)
        if match:
            flush();current=(match.group(1),[(match.group(2),entry)])
        elif current is not None:current[1].append((text,entry))
    flush()
    if not lines:warnings.append('품목 표 미인식. 원본을 확인하여 입력하세요.')
    if total is not None and lines and all(line['source_amount'].value is not None for line in lines):
        with localcontext() as context:
            context.prec=60
            if sum(Decimal(line['source_amount'].value) for line in lines)!=total:warnings.append('품목 공급가액 합계가 원문 총액과 다릅니다. 원본을 확인하세요.')
    return ExtractionResult(fields,tuple(lines),tuple(warnings),'review',tuple(evidence))

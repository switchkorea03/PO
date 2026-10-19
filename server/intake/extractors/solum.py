"""Read SOLUM VINA's wrapped table cells by PDF column coordinates."""
import re
from datetime import datetime
from .base import Evidence,ExtractedField,ExtractionResult

NUMBER=r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
KEYS=('code','name','quantity','unit','unit_price','currency','source_amount','requested_due')

def boxes(textpage,term):
    search=textpage.search(term,match_case=False);result=[]
    try:
        while (match:=search.get_next()):
            index,count=match;chars=[textpage.get_charbox(n) for n in range(index,index+count)]
            result.append((min(b[0] for b in chars),min(b[1] for b in chars),max(b[2] for b in chars),max(b[3] for b in chars)))
    finally:search.close()
    return result

def date_value(value):
    try:return datetime.strptime(value.strip(),'%m/%d/%Y').date().isoformat()
    except ValueError:return None

def extract_page(textpage,page,width,known=False):
    text=textpage.get_text_range()
    buyer=re.search(r'\(Company\)\s*(SOLU\s*M\s+VINA\s+CO\s*[.,]*\s*LTD)',text,re.I)
    if not buyer and not known:return None
    materials=boxes(textpage,'MATERIAL/VENDOR MATERIAL')
    if not materials:return None
    material=materials[0];height=material[3]-material[1];scale=max(height/7,.1)
    def header(term):
        return next((b for b in boxes(textpage,term) if abs(b[1]-material[1])<35*scale),None)
    price,quantity,unit,amount,charge,spec,delivery=[header(term) for term in ('PRICE','QUANTITY/','UNIT','AMOUNT','OTHER CHARGE','SPECIFICATION','[MM/DD/YYYY]')]
    if any(v is None for v in (price,quantity,unit,amount,charge,spec,delivery)):return None
    left=material[0]-5*scale;price_left=material[2]+4*scale;price_right=price[2]+4*scale
    quantity_right=max(quantity[2],unit[2])+4*scale;amount_right=max(amount[2],charge[2])+6*scale
    top=min(spec[1],unit[1],delivery[1])-3*scale
    footers=[b for b in boxes(textpage,'TOTAL') if b[3]<top]
    bottom=max((b[3] for b in footers),default=40*scale)+5*scale
    fields={key:ExtractedField(None) for key in ('po_number','customer_name','ordered_on','received_on','contact','etd','order_type')}
    def field(key,value,raw):fields[key]=ExtractedField(value,(Evidence(page,None,None,raw),))
    if buyer:
        field('customer_name','솔루엠(베트남향)',buyer.group(0));field('order_type','overseas',buyer.group(0))
    match=re.search(r'\(PO\s*No\.?\)\s*([\w-]+)',text,re.I)
    if match:field('po_number',match.group(1),match.group(0))
    match=re.search(r'\bDATE\s*:\s*(\d{1,2}/\d{1,2}/\d{4})',text,re.I)
    if match:field('ordered_on',date_value(match.group(1)),match.group(0))
    match=re.search(r'CURRENCY\s*:\s*([A-Z]{3})\b',text)
    currency=match.group(1) if match else None
    currency_evidence=(Evidence(page,None,None,match.group(0)),) if match else ()
    # The leftmost column contains item numbers, not quantities or PO dates.
    numbers=re.findall(r'^\s*(\d{1,6})\s*$',textpage.get_text_bounded(0,bottom,left,top),re.M)
    anchors={}
    for number in numbers:
        for b in boxes(textpage,number):
            if 0<=b[0]<b[2]<left and bottom<b[1]<b[3]<top:anchors[round((b[1]+b[3])/2,2)]=b
    rows=sorted(anchors.values(),key=lambda b:b[3],reverse=True);lines=[];warnings=[]
    for index,anchor in enumerate(rows):
        upper=top if index==0 else rows[index][3]+8*scale
        lower=rows[index+1][3]+8*scale if index+1<len(rows) else bottom
        def cell(a,b):return textpage.get_text_bounded(a,lower,b,upper).strip()
        material_text=cell(left,price_left);parts=material_text.splitlines()
        if not parts:continue
        code,_,vendor=parts[0].partition('/')
        code=code.strip()
        if not re.fullmatch(r'[A-Za-z0-9][\w.\-/]*',code):continue
        line={key:ExtractedField(None) for key in KEYS}
        def value(key,parsed,raw):line[key]=ExtractedField(parsed,(Evidence(page,None,None,f'품목 {index+1} / {key}: {raw}'),))
        value('code',code,parts[0]);description=vendor.strip()
        for part in parts[1:]:
            separator='' if description.endswith(('.','-')) and part[:1].isdigit() else ' '
            description+=separator+part.strip()
        value('name',description.strip() or None,material_text)
        raw_quantity=cell(price_right,quantity_right);compact=re.sub(r'\s+','',raw_quantity)
        match=re.fullmatch(r'('+NUMBER+r')([A-Za-z]{1,8})?',compact)
        value('quantity',match.group(1).replace(',','') if match else None,raw_quantity)
        unit_match=re.search(r'([A-Za-z]{1,8})$',compact)
        value('unit',unit_match.group(1) if unit_match else None,raw_quantity)
        for key,a,b in [('unit_price',price_left,price_right),('source_amount',quantity_right,amount_right)]:
            raw=cell(a,b);number=re.sub(r'\s+','',raw)
            value(key,number.replace(',','') if re.fullmatch(NUMBER,number) else None,raw)
        raw_due=cell(delivery[0]-3*scale,min(width,delivery[2]+5*scale))
        value('requested_due',date_value(re.sub(r'\s+','',raw_due)),raw_due)
        line['currency']=ExtractedField(currency,currency_evidence)
        for key in ('quantity','unit_price','source_amount','requested_due'):
            if line[key].value is None:warnings.append(f'{page}페이지 품목 {index+1}: {key} 값을 원본에서 확인하세요.')
        lines.append(line)
    return ExtractionResult(fields,tuple(lines),tuple(warnings),'review')

def combine(pages,evidence):
    fields={};lines=[];warnings=[];conflicts=set()
    for result in pages:
        lines.extend(result.lines);warnings.extend(result.warnings)
        for key,field in result.fields.items():
            if key in conflicts:continue
            if key in fields and fields[key].value and field.value and fields[key].value!=field.value:
                fields[key]=ExtractedField(None,fields[key].evidence+field.evidence);conflicts.add(key)
                warnings.append(f'페이지별 {key} 값이 다릅니다. 원본을 확인하세요.')
            elif key not in fields or not fields[key].value:fields[key]=field
    if not lines:warnings.append('품목 표를 판독하지 못했습니다. 수동입력으로 등록하세요.')
    warnings.append('솔루엠 베트남 양식: 수량의 셀 안 줄바꿈을 연결했습니다. 원본과 비교한 후 확정하세요.')
    warnings.append('해외 원문 납기는 일정에 사용하지 않습니다. PO 수령일과 ETD는 별도로 확인하세요.')
    return ExtractionResult(fields,tuple(lines),tuple(dict.fromkeys(warnings)),'review',tuple(evidence))

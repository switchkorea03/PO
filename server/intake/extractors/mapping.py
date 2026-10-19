import re
from collections import defaultdict
from datetime import date
from .base import ExtractedField,ExtractionResult

ALIASES={
 'code':['품목코드','제품코드','모델명','모델','itemcode','partno','partnumber','model','code'],
 'name':['품명','품목명','제품명','description','itemname','name'],
 'quantity':['수량','주문수량','quantity','qty'],
 'unit':['단위','unit','uom'],
 'unit_price':['단가','unitprice','price'],
 'currency':['통화','currency'],
 'source_amount':['공급가액','금액','amount','totalamount'],
 'requested_due':['납기일','납기','요청납기일','요청납기','duedate','deliverydate'],
 'po_number':['po번호','발주번호','pono','ponumber','purchaseorderno'],
 'customer_name':['고객명','고객사명','고객사','customer','customername','buyer'],
 'ordered_on':['주문일','발주일','orderdate','podate'],
 'received_on':['수령일','receiveddate'],
 'contact':['담당자','고객담당자','contact']}
def norm(value):return re.sub(r'[^a-z0-9가-힣]','',value.lower())
def key_for(label):
    normal=norm(label)
    return next((key for key,aliases in ALIASES.items() if normal in aliases),None)

def map_evidence(evidence,customer_id=None):
    fields={key:ExtractedField(None) for key in ['po_number','customer_name','ordered_on','received_on','contact','etd']}
    lines=[];warnings=[];rows=[]
    grouped={}
    for e in evidence:
        if e.cell:
            rowkey=(e.sheet,re.sub(r'\D','',e.cell))
            if rowkey not in grouped:grouped[rowkey]=[];rows.append(grouped[rowkey])
            grouped[rowkey].append((e.text,e))
        else:
            parts=re.split(r'\s*\|\s*|\t|\s{2,}',e.text.strip())
            rows.append([(part,e) for part in parts])
    header=None;context=None
    for row in rows:
        if not row:continue
        current=(row[0][1].sheet,row[0][1].page)
        if current!=context:header=None;context=current
        values=[v for v,_ in row];keys=[key_for(v) for v in values]
        if 'quantity' in keys and ('code' in keys or 'name' in keys):header=keys;continue
        if len(row)>=2 and keys[0] in fields:
            fields[keys[0]]=ExtractedField(row[1][0],(row[1][1],));continue
        full=' '.join(values)
        for label,key in [(r'PO\s*(?:No\.?|Number|번호)','po_number'),(r'(?:Customer|고객사명|고객명)','customer_name'),(r'(?:Order Date|발주일|주문일)','ordered_on')]:
            match=re.match(label+r'\s*[:：]\s*(.+)',full,re.I)
            if match:fields[key]=ExtractedField(match.group(1).strip(),(row[0][1],))
        if header and len(row)>1:
            line={key:ExtractedField(None) for key in ['code','name','quantity','unit','unit_price','currency','source_amount','requested_due']}
            for idx,key in enumerate(header):
                if key in line and idx<len(row):
                    value,e=row[idx]
                    if value.startswith('='):
                        warnings.append(f'{e.sheet or e.page} {e.cell or ""}: 수식 저장값 없음 · 직접 확인')
                        value=None
                    line[key]=ExtractedField(value or None,(e,))
            if line['code'].value or line['name'].value:
                for key in ['quantity','unit_price','source_amount']:
                    value=line[key].value
                    if value is not None and not re.fullmatch(r'[+-]?\d+(?:\.\d+)?',value.replace(',','')):
                        line[key]=ExtractedField(None,line[key].evidence)
                lines.append(line)
    if not lines:warnings.append('품목 표를 판독하지 못했습니다. 수동입력으로 등록하세요.')
    warnings.append('인식값을 원본과 비교한 후 확정하세요.')
    return ExtractionResult(fields,tuple(lines),tuple(dict.fromkeys(warnings)),'review',tuple(evidence))

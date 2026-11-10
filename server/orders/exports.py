"""Excel snapshots of the same filtered PO rows shown in the list."""
from io import BytesIO
from decimal import Decimal
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


HEADERS=['발주서 등록일','고객사','구분','PO번호','자사품목명','고객품목명','스펙',
         '수량','단위','단가','공급가액','통화','납기일','출고수량','잔량','상태']


def excel_value(value):
    if isinstance(value,Decimal):
        text=format(value,'f')
        if '.' in text:text=text.rstrip('0').rstrip('.')
        # Excel numeric cells support 15 significant digits. Preserve larger
        # values as literal text instead of silently rounding business data.
        if len(text.replace('.','').lstrip('-0'))>15:return text
    return value


def orders_workbook(orders):
    workbook=Workbook();sheet=workbook.active;sheet.title='PO 목록'
    sheet.append(HEADERS);sheet.freeze_panes='A2';sheet.row_dimensions[1].height=28
    widths=[16,22,10,24,22,22,42,18,10,18,20,10,16,18,18,12]
    for index,width in enumerate(widths,1):sheet.column_dimensions[get_column_letter(index)].width=width
    for cell in sheet[1]:
        cell.font=Font(name='맑은 고딕',bold=True,color='FFFFFF')
        cell.fill=PatternFill('solid',fgColor='255FE8')
        cell.alignment=Alignment(vertical='center')
    for order in orders:
        for line in order.lines.all():
            shipped=line.shipped;remaining=line.quantity-shipped-line.cancelled_quantity
            status='휴지통' if order.is_deleted else '취소' if order.cancelled else '출고 완료' if remaining==0 else '진행 중'
            values=[timezone.localtime(order.created_at).date(),order.customer.name,
                order.get_order_type_display(),order.po_number,line.resolved_internal_name,
                line.code or line.name,line.name,
                line.quantity,line.unit,line.unit_price,line.amount,line.currency,
                line.requested_due,shipped,remaining,status]
            sheet.append([excel_value(value) for value in values])
            for cell,value in zip(sheet[sheet.max_row],values):
                cell.font=Font(name='맑은 고딕',size=11)
                cell.alignment=Alignment(vertical='top',wrap_text=cell.column==7)
                if isinstance(value,str):cell.data_type='s'
                if isinstance(value,Decimal):
                    cell.alignment=Alignment(horizontal='right',vertical='top')
                    fraction=len(format(value,'f').rstrip('0').split('.')[-1]) if '.' in format(value,'f') else 0
                    cell.number_format='#,##0' if value==value.to_integral_value() else '#,##0.'+'#'*fraction
                if cell.column in (1,13):cell.number_format='yyyy-mm-dd'
    sheet.auto_filter.ref=f'A1:P{sheet.max_row}'
    sheet.print_title_rows='1:1';sheet.sheet_properties.pageSetUpPr.fitToPage=True
    sheet.page_setup.orientation='landscape';sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=0
    output=BytesIO();workbook.save(output);workbook.close();output.seek(0)
    return output

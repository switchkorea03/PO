from datetime import datetime,date
from .base import Evidence
from .mapping import map_evidence

def cell_text(value):
    if value is None:return ''
    if isinstance(value,(datetime,date)):return value.date().isoformat() if isinstance(value,datetime) else value.isoformat()
    return str(value)

def extract_excel(path,extension):
    evidence=[];count=0
    if extension=='.xlsx':
        from openpyxl import load_workbook
        from openpyxl.utils.cell import get_column_letter
        values=load_workbook(path,read_only=True,data_only=True)
        formulas=load_workbook(path,read_only=True,data_only=False)
        try:
            for sheet in values:
                formula_sheet=formulas[sheet.title]
                for row_number,(value_row,formula_row) in enumerate(zip(sheet.iter_rows(),formula_sheet.iter_rows()),1):
                    for column_number,(cell,raw) in enumerate(zip(value_row,formula_row),1):
                        count+=1
                        if count>200000:raise ValueError('Excel 20만 셀 제한 초과 · 직접 입력하세요.')
                        value=cell.value if cell.value is not None else (raw.value if raw.data_type=='f' else None)
                        # Blank cells retain their positions in tabular rows.
                        evidence.append(Evidence(None,sheet.title,f'{get_column_letter(column_number)}{row_number}',cell_text(value)))
        finally:values.close();formulas.close()
    else:
        import xlrd
        from openpyxl.utils.cell import get_column_letter
        book=xlrd.open_workbook(str(path),on_demand=True)
        try:
            for sheet in book.sheets():
                if count+sheet.nrows*sheet.ncols>200000:raise ValueError('Excel 20만 셀 제한 초과 · 직접 입력하세요.')
                for row in range(sheet.nrows):
                    for col in range(sheet.ncols):
                        cell=sheet.cell(row,col);value=cell.value
                        if cell.ctype==xlrd.XL_CELL_DATE:value=xlrd.xldate_as_datetime(value,book.datemode).date()
                        if isinstance(value,float) and value.is_integer():value=int(value)
                        evidence.append(Evidence(None,sheet.name,f'{get_column_letter(col+1)}{row+1}',cell_text(value)));count+=1
        finally:book.release_resources()
    return map_evidence(tuple(evidence))

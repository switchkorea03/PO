def render_notice(items,on):
    today=[];overdue=[]
    for item in items:
        text=f'{item.customer_name} / {item.po_number} · {item.title}'
        if item.open_steps:text+=' — '+', '.join(item.open_steps)
        (today if item.effective_on==on else overdue).append(text)
    sections=[f'[PO 업무 알림 {on:%m/%d}]']
    if today:sections.append('오늘\n'+'\n'.join(today))
    if overdue:sections.append('지연\n'+'\n'.join(overdue))
    return '\n\n'.join(sections)+'\n\n상세는 업무 달력에서 확인하세요.'

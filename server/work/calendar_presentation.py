"""Company-first calendar display; task scheduling and API data stay unchanged."""
from collections import defaultdict


def day_summary(tasks,dues,on,today):
    tasks=[task for task in tasks if task['state']!='cancelled']
    companies={str(task['customer_id']) for task in tasks}
    companies.update(str(due['customer_id']) for due in dues)
    grouped=defaultdict(list)
    for task in tasks:grouped[(str(task['customer_id']),task['kind'])].append(task)
    entries=[]
    for items in grouped.values():
        first=items[0]
        active=[item for item in items if not item['suspended']]
        pending=[item for item in active if item['state']!='done']
        if not active:status,tone,priority='보류','muted',4
        elif not pending:status,tone,priority='완료','done',3
        elif on<today:status,tone,priority='지연','late',0
        elif any(item['state'] in ('done','partial') for item in active):status,tone,priority='부분완료','planned',1
        else:status,tone,priority='예정','planned',1
        entries.append({'customer_key':str(first['customer_id']),'customer_name':first['customer_name'],'title':first['title'],
                        'status':status,'tone':tone,'priority':priority,'task_count':len(items),
                        'links':[{'url':f"/tasks/{item['id']}/",'label':item.get('po_number') or '업무 상세'} for item in items]})
    for due in dues:
        entries.append({'customer_key':str(due['customer_id']),'customer_name':due['customer_name'],'title':'납기일','status':'납기','tone':'due','priority':2,'task_count':0,
                        'links':[{'url':due['url'],'label':'납기 내역'}]})
    entries.sort(key=lambda item:(item['priority'],item['customer_name'],item['title']))
    blocks={}
    for entry in entries:
        block=blocks.setdefault(entry['customer_key'],{'key':entry['customer_key'],'name':entry['customer_name'],'tone':entry['tone'],'items':[]})
        block['items'].append(entry)
    return {'customer_count':len(companies),'pending_count':sum(task['state']!='done' and not task['suspended'] for task in tasks),
            'company_blocks':list(blocks.values()),'schedule_count':len(entries)}

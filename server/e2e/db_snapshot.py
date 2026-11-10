"""Read-only DB evidence for the no-upload browser integration test."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.e2e_settings'
import django
django.setup()
from django.conf import settings
from django.db import connection
from orders.models import Order
from intake.models import SourceFile

assert settings.DATABASES['default']['NAME'] == 'po_calendar_e2e'
assert connection.vendor == 'postgresql'
with connection.cursor() as cursor:
    cursor.execute('SELECT current_database()')
    database = cursor.fetchone()[0]
assert database == 'po_calendar_e2e'
order = Order.objects.select_related('customer').get(po_number=sys.argv[1])
result = {
    'database': database,
    'engine': connection.vendor,
    'id': str(order.id),
    'number': order.po_number,
    'type': order.order_type,
    'customer': order.customer.name,
    'received_on': str(order.received_on),
    'lines': [{'code': line.code, 'name': line.name, 'quantity': str(line.quantity),
               'shipped': str(line.shipped), 'remaining': str(line.remaining),
               'amount': str(line.amount)} for line in order.lines.order_by('code')],
    'shipments': [{'sequence': row.sequence, 'completed': row.completed,
                   'ship_on': str(row.ship_on), 'etd': str(row.etd), 'eta': str(row.eta)}
                  for row in order.shipments.order_by('sequence')],
    'tasks': [{'id': str(task.id), 'kind': task.kind, 'date': str(task.effective_on),
               'state': task.state, 'suspended': task.suspended,
               'done_steps': task.substeps.filter(done=True).count()}
              for task in order.tasks.order_by('kind', 'scope_key')],
    'audit': list(order.history.values_list('action', flat=True)),
    'attached_sources': order.source_versions.count(),
    'uploaded_file_count': SourceFile.objects.count(),
}
print(json.dumps(result, ensure_ascii=True))

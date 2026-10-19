from django.db import migrations,models
from django.db.models import Count

def merge_duplicate_customers(apps,schema_editor):
    Customer=apps.get_model('orders','Customer');Order=apps.get_model('orders','Order')
    alias=schema_editor.connection.alias
    duplicates=Customer.objects.using(alias).values('name').annotate(total=Count('id')).filter(total__gt=1)
    for group in list(duplicates):
        customers=list(Customer.objects.using(alias).filter(name=group['name']).annotate(po_count=Count('orders')).order_by('-po_count','id'))
        keeper=customers[0]
        for duplicate in customers[1:]:
            numbers=Order.objects.using(alias).filter(customer=keeper).values_list('po_number',flat=True)
            if Order.objects.using(alias).filter(customer=duplicate,po_number__in=numbers).exists():
                raise RuntimeError('같은 고객명과 PO 번호의 기존 기록이 충돌합니다. PO 이력을 보존하여 정리한 후 다시 실행하세요.')
            Order.objects.using(alias).filter(customer=duplicate).update(customer=keeper)
            duplicate.delete(using=alias)

class Migration(migrations.Migration):
    dependencies=[('orders','0002_changeevent_consumed_at')]
    operations=[
        migrations.RunPython(merge_duplicate_customers,migrations.RunPython.noop),
        # Reassigned orders use deferred FK checks; flush them before ALTER TABLE.
        migrations.RunSQL('SET CONSTRAINTS ALL IMMEDIATE',migrations.RunSQL.noop),
        migrations.AlterField(model_name='customer',name='name',field=models.CharField(max_length=200,unique=True)),
    ]

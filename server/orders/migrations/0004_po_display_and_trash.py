from django.db import migrations, models

def seed_customers_and_items(apps,schema_editor):
    Customer=apps.get_model('orders','Customer')
    Line=apps.get_model('orders','OrderLine')
    for name,kind in [('범진전자','domestic'),('SJI','domestic'),('SJIT','domestic'),
                      ('켐트로비나','overseas'),('솔루엠','overseas'),('리모트솔루션','overseas')]:
        customer,created=Customer.objects.get_or_create(name=name,defaults={'default_type':kind,'currency':'KRW' if kind=='domestic' else 'USD'})
        if not created and customer.default_type!=kind:
            customer.default_type=kind;customer.save(update_fields=['default_type'])
    for code,internal in [('MESA10005A','JT1138BEM'),('MESA10007A','JT1140WJ-BEM'),
                          ('MESA10008A','JTP1169BEM'),('MESAH0002A','JT1280A6')]:
        from django.db.models import Q
        Line.objects.filter(Q(code__iexact=code)|Q(name__iexact=code),internal_name='').update(internal_name=internal)

class Migration(migrations.Migration):
    dependencies=[('orders','0003_unique_customer_name')]
    operations=[
        migrations.AddField(model_name='order',name='is_deleted',field=models.BooleanField(default=False,db_index=True)),
        migrations.AddField(model_name='order',name='deleted_at',field=models.DateTimeField(null=True,blank=True)),
        migrations.AddField(model_name='orderline',name='internal_name',field=models.CharField(max_length=200,blank=True)),
        migrations.RunPython(seed_customers_and_items,migrations.RunPython.noop),
    ]

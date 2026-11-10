from django.core.management.base import BaseCommand
from orders.models import Customer

class Command(BaseCommand):
    help='Register the six default customer groups without deleting existing customers.'
    def handle(self,*args,**options):
        for name,kind in [('범진전자','domestic'),('SJI','domestic'),('SJIT','domestic'),('켐트로비나','overseas'),('솔루엠','overseas'),('리모트솔루션','overseas')]:
            customer,created=Customer.objects.get_or_create(name=name,defaults={'default_type':kind,'currency':'KRW' if kind=='domestic' else 'USD'})
            if customer.default_type!=kind:customer.default_type=kind;customer.save(update_fields=['default_type'])
        self.stdout.write('PO customer defaults ready (6).')

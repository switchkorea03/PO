import uuid
from decimal import Decimal, localcontext
from django.conf import settings
from django.db import models
from django.db.models import Q

class Customer(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=200)
    contact=models.CharField(max_length=200,blank=True)
    default_type=models.CharField(max_length=12,default="domestic")
    currency=models.CharField(max_length=3,default="KRW")
    class Meta:
        ordering=["name","id"]
    def __str__(self): return self.name

class Order(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    customer=models.ForeignKey(Customer,on_delete=models.PROTECT,related_name="orders")
    po_number=models.CharField(max_length=120)
    order_type=models.CharField(max_length=12,choices=[("domestic","국내"),("overseas","해외")])
    erp_type=models.CharField(max_length=16,default="unspecified")
    ordered_on=models.DateField(null=True,blank=True)
    received_on=models.DateField(null=True,blank=True)
    contact=models.CharField(max_length=200,blank=True)
    note=models.TextField(blank=True)
    cancelled=models.BooleanField(default=False)
    row_version=models.PositiveIntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["customer","po_number"],name="unique_customer_po")]
        ordering=["-created_at"]
    def __str__(self): return f"{self.customer.name} / {self.po_number}"

class OrderLine(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="lines")
    code=models.CharField(max_length=120,blank=True)
    name=models.CharField(max_length=300)
    quantity=models.DecimalField(max_digits=30,decimal_places=10)
    cancelled_quantity=models.DecimalField(max_digits=30,decimal_places=10,default=0)
    unit=models.CharField(max_length=30)
    unit_price=models.DecimalField(max_digits=30,decimal_places=10,null=True,blank=True)
    currency=models.CharField(max_length=3,default="KRW")
    source_amount=models.DecimalField(max_digits=60,decimal_places=20,null=True,blank=True)
    requested_due=models.DateField(null=True,blank=True)
    class Meta:
        ordering=["id"]
        constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name="positive_line_qty"),models.CheckConstraint(condition=Q(cancelled_quantity__gte=0)&Q(cancelled_quantity__lte=models.F("quantity")),name="valid_cancelled_qty")]
    @property
    def amount(self):
        if self.unit_price is None: return None
        with localcontext() as ctx:
            ctx.prec=65
            return self.quantity*self.unit_price
    @property
    def amount_mismatch(self): return self.source_amount is not None and self.amount is not None and self.source_amount!=self.amount
    @property
    def shipped(self):
        return self.allocations.filter(shipment__completed=True,shipment__cancelled=False).aggregate(v=models.Sum("quantity"))["v"] or Decimal(0)
    @property
    def remaining(self): return self.quantity-self.shipped-self.cancelled_quantity
    @property
    def allocated(self):
        return self.allocations.filter(shipment__cancelled=False).aggregate(v=models.Sum("quantity"))["v"] or Decimal(0)

class Shipment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="shipments")
    sequence=models.PositiveIntegerField()
    ship_on=models.DateField(null=True,blank=True)
    etd=models.DateField(null=True,blank=True)
    eta=models.DateField(null=True,blank=True)
    completed=models.BooleanField(default=False)
    cancelled=models.BooleanField(default=False)
    completed_at=models.DateTimeField(null=True,blank=True)
    completed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    row_version=models.PositiveIntegerField(default=1)
    class Meta:
        ordering=["sequence"]
        constraints=[models.UniqueConstraint(fields=["order","sequence"],name="unique_shipment_sequence")]

class ShipmentLine(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    shipment=models.ForeignKey(Shipment,on_delete=models.CASCADE,related_name="allocations")
    line=models.ForeignKey(OrderLine,on_delete=models.PROTECT,related_name="allocations")
    quantity=models.DecimalField(max_digits=30,decimal_places=10)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["shipment","line"],name="unique_shipment_line"),models.CheckConstraint(condition=Q(quantity__gt=0),name="positive_shipment_qty")]

class AuditEntry(models.Model):
    id=models.BigAutoField(primary_key=True)
    order=models.ForeignKey(Order,on_delete=models.PROTECT,related_name="history")
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    action=models.CharField(max_length=100)
    target=models.CharField(max_length=100)
    before=models.JSONField(default=dict)
    after=models.JSONField(default=dict)
    reason=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-id"]

class ChangeEvent(models.Model):
    id=models.BigAutoField(primary_key=True)
    public_id=models.UUIDField(default=uuid.uuid4,unique=True)
    order=models.ForeignKey(Order,on_delete=models.PROTECT)
    affected_task_ids=models.JSONField(default=list)
    eligibility=models.JSONField(default=list)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    occurred_at=models.DateTimeField()
    consumed_at=models.DateTimeField(null=True,blank=True,db_index=True)

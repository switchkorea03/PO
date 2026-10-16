import uuid
from django.db import models
from django.conf import settings
class Task(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    order=models.ForeignKey("orders.Order",on_delete=models.PROTECT,related_name="tasks")
    shipment=models.ForeignKey("orders.Shipment",on_delete=models.PROTECT,null=True,blank=True,related_name="tasks")
    scope_key=models.CharField(max_length=80)
    kind=models.CharField(max_length=40)
    title=models.CharField(max_length=200)
    basis_on=models.DateField(null=True,blank=True)
    auto_on=models.DateField(null=True,blank=True)
    manual_on=models.DateField(null=True,blank=True)
    effective_on=models.DateField(null=True,blank=True,db_index=True)
    state=models.CharField(max_length=16,default="open")
    suspended=models.BooleanField(default=False)
    needs_review=models.BooleanField(default=False)
    recalc_needed=models.BooleanField(default=False)
    row_version=models.PositiveIntegerField(default=1)
    notice_revision=models.PositiveIntegerField(default=1)
    dependency_hash=models.CharField(max_length=64,blank=True)
    completed_at=models.DateTimeField(null=True,blank=True)
    completed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    class Meta:
        ordering=["effective_on","kind","id"]
        constraints=[models.UniqueConstraint(fields=["scope_key","kind"],name="unique_work_scope_kind")]
    @property
    def open_steps(self): return tuple(self.substeps.filter(done=False).values_list("label",flat=True))
class Substep(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey(Task,on_delete=models.CASCADE,related_name="substeps")
    label=models.CharField(max_length=300)
    position=models.PositiveIntegerField(default=0)
    done=models.BooleanField(default=False)
    completed_at=models.DateTimeField(null=True,blank=True)
    completed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    class Meta:
        ordering=["position","id"]
        constraints=[models.UniqueConstraint(fields=["task","position"],name="unique_substep_position")]

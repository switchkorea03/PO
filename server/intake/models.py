import uuid
from django.conf import settings
from django.db import models

class SourceFile(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    sha256=models.CharField(max_length=64,unique=True)
    path=models.TextField()
    original_name=models.CharField(max_length=250)
    extension=models.CharField(max_length=8)
    size=models.PositiveBigIntegerField()
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)

class ExtractionJob(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    source=models.OneToOneField(SourceFile,on_delete=models.PROTECT,related_name='job')
    status=models.CharField(max_length=16,default='pending')
    lease_until=models.DateTimeField(null=True,blank=True)
    attempts=models.PositiveIntegerField(default=0)
    error=models.TextField(blank=True)
    started_at=models.DateTimeField(null=True,blank=True)
    finished_at=models.DateTimeField(null=True,blank=True)

class ExtractionDraft(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    job=models.OneToOneField(ExtractionJob,on_delete=models.PROTECT,related_name='draft')
    result=models.JSONField(default=dict)
    row_version=models.PositiveIntegerField(default=1)
    confirmed_order=models.ForeignKey('orders.Order',on_delete=models.PROTECT,null=True,blank=True)

class OrderSource(models.Model):
    order=models.ForeignKey('orders.Order',on_delete=models.PROTECT,related_name='source_versions')
    source=models.ForeignKey(SourceFile,on_delete=models.PROTECT,related_name='order_versions')
    version=models.PositiveIntegerField()
    confirmed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-version']
        constraints=[models.UniqueConstraint(fields=['order','version'],name='unique_source_version'),models.UniqueConstraint(fields=['order','source'],name='unique_order_source')]

class GeminiDailyUsage(models.Model):
    day=models.DateField(primary_key=True)
    calls=models.PositiveIntegerField(default=0)

class GeminiReview(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    draft=models.ForeignKey(ExtractionDraft,on_delete=models.PROTECT,related_name='gemini_reviews')
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    model=models.CharField(max_length=100)
    draft_version=models.PositiveIntegerField()
    status=models.CharField(max_length=16,default='running')
    original_result=models.JSONField(default=dict)
    result=models.JSONField(default=dict)
    usage=models.JSONField(default=dict)
    error=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    finished_at=models.DateTimeField(null=True,blank=True)
    applied_at=models.DateTimeField(null=True,blank=True)

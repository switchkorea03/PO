import uuid
from django.db import models
from django.conf import settings

class NoticeSettings(models.Model):
    id=models.PositiveSmallIntegerField(primary_key=True,default=1,editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    recipient=models.CharField(max_length=20,blank=True)
    sender=models.CharField(max_length=20,blank=True)
    enabled=models.BooleanField(default=False)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(id=1),name='single_notice_settings')]

class NoticeBatch(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    settings=models.ForeignKey(NoticeSettings,on_delete=models.PROTECT)
    business_date=models.DateField()
    kind=models.CharField(max_length=16)
    key=models.CharField(max_length=200,unique=True)
    recipient=models.CharField(max_length=20)
    sender=models.CharField(max_length=20)
    status=models.CharField(max_length=20,default='pending',db_index=True)
    body=models.TextField(blank=True)
    error=models.TextField(blank=True)
    lease_until=models.DateTimeField(null=True,blank=True)
    lease_token=models.UUIDField(null=True,blank=True)
    next_attempt_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

class NoticeItem(models.Model):
    batch=models.ForeignKey(NoticeBatch,on_delete=models.CASCADE,related_name='items')
    task=models.ForeignKey('work.Task',on_delete=models.PROTECT)
    notice_revision=models.PositiveIntegerField()
    event_id=models.BigIntegerField(null=True,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['batch','task'],name='unique_notice_item')]

class DailyRun(models.Model):
    settings=models.ForeignKey(NoticeSettings,on_delete=models.PROTECT)
    business_date=models.DateField()
    batch=models.ForeignKey(NoticeBatch,on_delete=models.PROTECT,null=True,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['settings','business_date'],name='unique_daily_run')]

class EventCursor(models.Model):
    id=models.PositiveSmallIntegerField(primary_key=True,default=1)
    last_event_id=models.BigIntegerField(default=0)

class NoticePart(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    batch=models.ForeignKey(NoticeBatch,on_delete=models.CASCADE,related_name='parts')
    position=models.PositiveIntegerField()
    client_key=models.CharField(max_length=80,unique=True,default=uuid.uuid4)
    body=models.TextField()
    status=models.CharField(max_length=20,default='pending')
    provider_id=models.CharField(max_length=150,null=True,blank=True)
    attempts=models.PositiveIntegerField(default=0)
    reason=models.TextField(blank=True)
    class Meta:
        ordering=['position']
        constraints=[models.UniqueConstraint(fields=['batch','position'],name='unique_notice_part')]

class SendAttempt(models.Model):
    part=models.ForeignKey(NoticePart,on_delete=models.PROTECT,related_name='history')
    number=models.PositiveIntegerField()
    status=models.CharField(max_length=20,default='sending')
    reason=models.TextField(blank=True)
    provider_id=models.CharField(max_length=150,null=True,blank=True)
    requested_at=models.DateTimeField()
    finished_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['part','number'],name='unique_send_attempt')]

class WorkerHeartbeat(models.Model):
    name=models.CharField(max_length=30,primary_key=True)
    updated_at=models.DateTimeField()

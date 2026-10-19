import time
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from notices.worker import run_once
class Command(BaseCommand):
    help='PO 문자 정기·추가 알림과 결과 복구를 처리합니다.'
    def add_arguments(self,parser):parser.add_argument('--once',action='store_true')
    def handle(self,*args,**options):
        if settings.SMS_PROVIDER=='fake' and settings.DEBUG:
            from notices.providers.fake import FakeSmsProvider
            provider=FakeSmsProvider()
        elif settings.SMS_PROVIDER=='solapi':
            from notices.providers.configured import ConfiguredSmsProvider
            provider=ConfiguredSmsProvider()
        else:raise CommandError('문자 공급자가 미설정입니다. .env와 문자 설정을 확인하세요. 실제 문자는 발송하지 않았습니다.')
        while True:
            count=run_once(provider)
            if options['once']:self.stdout.write(f'{count}개 문자 묶음 확인');return
            time.sleep(30)

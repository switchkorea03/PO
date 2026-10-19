import time
from django.core.management.base import BaseCommand
from intake.worker import run_pending
class Command(BaseCommand):
    help='로컬 PO 파일 인식 작업을 처리합니다.'
    def add_arguments(self,parser):parser.add_argument('--once',action='store_true')
    def handle(self,*args,**options):
        while True:
            count=run_pending()
            if options['once']:self.stdout.write(f'{count}개 작업 확인');return
            time.sleep(3)

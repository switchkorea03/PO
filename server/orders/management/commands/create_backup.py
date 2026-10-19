from pathlib import Path
from django.core.management.base import BaseCommand
from common.backup import create_backup
class Command(BaseCommand):
    def add_arguments(self,parser):parser.add_argument('--destination',required=True)
    def handle(self,*args,**options):
        result=create_backup(Path(options['destination']));self.stdout.write(f"백업 검증 완료: PO {result['counts']['orders']}건, 파일 {len(result['files'])}개")

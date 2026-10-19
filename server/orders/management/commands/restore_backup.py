from pathlib import Path
from django.core.management.base import BaseCommand
from common.backup import restore_backup
class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--source',required=True);parser.add_argument('--target-database',required=True);parser.add_argument('--target-media',required=True)
    def handle(self,*args,**options):
        result=restore_backup(Path(options['source']),options['target_database'],Path(options['target_media']));self.stdout.write(f"복구 검증 완료: {result['counts']}; 실제 문자 비활성")

import tempfile,uuid
from pathlib import Path
from django.test import TransactionTestCase,override_settings
from django.db import connection
from django.contrib.auth import get_user_model
from orders.tests.factories import make_order,make_shipment
from work.services import set_substep
from intake.services import upload_source
from intake.models import OrderSource
from django.core.files.uploadedfile import SimpleUploadedFile
from intake.tests.test_upload import excel_bytes
from common.backup import create_backup,restore_backup

class BackupTests(TransactionTestCase):
    def test_real_dump_and_restore_preserve_data_files_and_completed_work(self):
        import psycopg
        from psycopg import sql
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with override_settings(PRIVATE_MEDIA_ROOT=root/'media',MAINTENANCE_FILE=root/'maintenance'):
                user=get_user_model().objects.create_user('backup-manager')
                order=make_order();make_shipment(order,'100',ship_on='2026-10-19')
                task=order.tasks.get(kind='domestic_share');set_substep(task.substeps.first().id,True,user.id,task.row_version)
                upload=upload_source(SimpleUploadedFile('original.xlsx',excel_bytes()),user.id)
                OrderSource.objects.create(order=order,source_id=upload.source_id,version=1,confirmed_by=user)
                manifest=create_backup(root/'snapshot')
                self.assertEqual(manifest['counts']['orders'],1);self.assertEqual(len(manifest['files']),1)
                target='po_test_'+uuid.uuid4().hex[:10]+'_restore'
                try:
                    report=restore_backup(root/'snapshot',target,root/'restored-media')
                    self.assertEqual(report['counts'],manifest['counts'])
                    self.assertEqual(report['completed_task_ids'],manifest['completed_task_ids'])
                    self.assertEqual(report['verified_files'],1)
                    self.assertFalse(Path(root/'maintenance').exists())
                finally:
                    cfg=connection.settings_dict
                    with psycopg.connect(host=cfg['HOST'],port=cfg['PORT'],user=cfg['USER'],password=cfg['PASSWORD'],dbname='postgres',autocommit=True) as c:c.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(target)))
    def test_refuses_current_database_and_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'backup').mkdir()
            with self.assertRaises(ValueError):create_backup(root/'backup')
            with self.assertRaises(ValueError):restore_backup(root,connection.settings_dict['NAME'],root/'media')

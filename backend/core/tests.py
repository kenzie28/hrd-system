from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.management.commands.ensure_schema import _missing_tables, _model_tables


class EnsureSchemaTests(TestCase):
    def test_verify_only_accepts_a_fully_migrated_database(self):
        call_command('ensure_schema', verify_only=True)
        self.assertEqual(_missing_tables(), [])

    def test_verification_covers_every_attendance_table(self):
        tables = _model_tables()
        self.assertEqual(tables['absensi_absensi'], 'absensi')
        self.assertEqual(tables['absensi_rekapabsensi'], 'absensi')
        self.assertEqual(tables['absensi_pendingattendanceday'], 'absensi')
        self.assertEqual(tables['absensi_pendingattendancemonth'], 'absensi')
        self.assertEqual(tables['karyawan_karyawan'], 'karyawan')

    def test_verify_only_reports_a_missing_model_table(self):
        from core.management.commands import ensure_schema as module

        original = module._missing_tables
        module._missing_tables = lambda: ['absensi_pendingattendanceday']
        try:
            with self.assertRaises(CommandError) as raised:
                call_command('ensure_schema', verify_only=True)
        finally:
            module._missing_tables = original
        self.assertIn('absensi_pendingattendanceday', str(raised.exception))

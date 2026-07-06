from django.core.management.base import BaseCommand

from attendance.payroll_import import DEFAULT_ID_COUNTER, DEFAULT_LOKASI_NAMA, import_payroll_absensi


class Command(BaseCommand):
    help = (
        'Import Karyawan and Absensi from the payroll MySQL database '
        '(sr_empl, sr_absensi). Self-contained; see attendance/payroll_import.py.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--id-counter',
            default=DEFAULT_ID_COUNTER,
            help=f'Payroll sr_absensi.id_counter / Lokasi id (default: {DEFAULT_ID_COUNTER})',
        )
        parser.add_argument(
            '--lokasi-nama',
            default=DEFAULT_LOKASI_NAMA,
            help=f'Lokasi nama when creating id from --id-counter (default: {DEFAULT_LOKASI_NAMA})',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report counts without writing to the HRD database',
        )

    def handle(self, *args, **options):
        result = import_payroll_absensi(
            id_counter=options['id_counter'],
            lokasi_nama=options['lokasi_nama'],
            dry_run=options['dry_run'],
        )

        prefix = '[dry-run] ' if options['dry_run'] else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'{prefix}Payroll import complete: '
                f'{result.karyawan_created} karyawan created, '
                f'{result.karyawan_existing} existing, '
                f'lokasi {"created" if result.lokasi_created else "already present"}, '
                f'{result.absensi_created} absensi created, '
                f'{result.absensi_updated} absensi updated, '
                f'{result.absensi_skipped} absensi skipped'
            )
        )

        if result.errors:
            self.stdout.write(self.style.WARNING(f'{len(result.errors)} issue(s):'))
            for msg in result.errors[:20]:
                self.stdout.write(f'  - {msg}')
            if len(result.errors) > 20:
                self.stdout.write(f'  ... and {len(result.errors) - 20} more')

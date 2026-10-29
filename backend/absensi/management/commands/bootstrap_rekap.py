from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db.models.functions import TruncMonth
from django.utils import timezone

from absensi.models import Absensi, Kehadiran, RekapAbsensi
from absensi.proses import proses_absensi_bulan
from cuti.models import Cuti
from lembur.models import PermohonanLembur


class Command(BaseCommand):
    help = 'Reconcile historical Kehadiran and Rekap Absensi using the incremental engine.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            help='Only reconcile one month (YYYY-MM). May be rerun safely.',
        )

    def handle(self, *args, **options):
        month_value = options.get('month')
        if month_value:
            try:
                months = {date.fromisoformat(f'{month_value}-01')}
            except ValueError as exc:
                raise CommandError('--month must use YYYY-MM format.') from exc
        else:
            months = set(RekapAbsensi.objects.values_list('month', flat=True))
            for model in (Absensi, Kehadiran, Cuti, PermohonanLembur):
                months.update(
                    date(value.year, value.month, 1)
                    for value in model.objects.annotate(
                        attendance_month=TruncMonth('tanggal')
                    )
                    .exclude(attendance_month=None)
                    .values_list('attendance_month', flat=True)
                    .distinct()
                )
            today = timezone.localdate()
            months.add(date(today.year, today.month, 1))

        for month in sorted(months):
            proses_absensi_bulan(month)
            self.stdout.write(self.style.SUCCESS(f'Reconciled {month:%Y-%m}'))

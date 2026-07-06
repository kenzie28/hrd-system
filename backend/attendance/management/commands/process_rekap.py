from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from attendance.services import process_rekap


def _parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise CommandError(f'Invalid date: {value!r} (expected YYYY-MM-DD)')


class Command(BaseCommand):
    help = 'Process (or reprocess) RekapKehadiran for a date range.'

    def add_arguments(self, parser):
        parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        start = _parse_date(options['start'])
        end = _parse_date(options['end'])
        if end < start:
            raise CommandError('--end must not be before --start')

        count = process_rekap(start, end)
        self.stdout.write(
            self.style.SUCCESS(f'Processed {count} rekap rows for {start} .. {end}')
        )

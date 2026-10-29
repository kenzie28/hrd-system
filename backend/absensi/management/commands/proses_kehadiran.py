from django.core.management.base import BaseCommand

from absensi.invalidation import close_yesterday


class Command(BaseCommand):
    help = 'Close yesterday and retry pending attendance materialization.'

    def handle(self, *args, **options):
        counts = close_yesterday()
        self.stdout.write(
            self.style.SUCCESS(
                'Kehadiran: '
                f"{counts['days']} hari, "
                f"{counts['months']} bulan, "
                f"{counts['failed']} gagal."
            )
        )

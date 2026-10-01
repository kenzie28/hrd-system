from django.core.management.base import BaseCommand

from absensi.kehadiran import proses_kehadiran


class Command(BaseCommand):
    help = 'Process past absensi, leave, and absences into Kehadiran rows.'

    def handle(self, *args, **options):
        counts = proses_kehadiran()
        self.stdout.write(
            self.style.SUCCESS(
                'Kehadiran: '
                f"{counts['hadir']} hadir, "
                f"{counts['cuti']} cuti, "
                f"{counts['alpa']} alpa."
            )
        )

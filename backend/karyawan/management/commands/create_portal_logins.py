from django.core.management.base import BaseCommand

from karyawan.models import Karyawan
from karyawan.services import create_portal_login


class Command(BaseCommand):
    help = 'Create portal login accounts (default password "123") for Karyawan without one.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reset the login/password for every Karyawan, even those already linked.',
        )

    def handle(self, *args, **options):
        queryset = Karyawan.objects.all()
        if not options['all']:
            queryset = queryset.filter(user__isnull=True)

        created = 0
        for karyawan in queryset:
            if not karyawan.karyawan_id:
                self.stdout.write(
                    self.style.WARNING(f'Skipping "{karyawan.nama}" (no karyawan_id).')
                )
                continue
            create_portal_login(karyawan)
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f'Portal logins created/reset for {created} employee(s).')
        )

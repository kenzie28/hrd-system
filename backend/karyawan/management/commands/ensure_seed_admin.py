from django.core.management.base import BaseCommand

from karyawan.seed import ensure_seed_admin


class Command(BaseCommand):
    help = (
        'Ensure HQ lokasi and default admin karyawan 0000003 (with portal login) exist.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-password',
            action='store_true',
            help='Reset portal password for 0000003 back to the default (123).',
        )

    def handle(self, *args, **options):
        message = ensure_seed_admin(force_password=options['force_password'])
        self.stdout.write(self.style.SUCCESS(message))

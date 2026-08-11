"""Ensure Django tables exist after migrate (recovers inconsistent MySQL volumes)."""

from __future__ import annotations

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


# Tables that must exist before seeding / serving traffic.
REQUIRED_MODELS = (
    'core.Lokasi',
    'karyawan.Karyawan',
    'auth.User',
    'authtoken.Token',
)


def _required_tables() -> dict[str, str]:
    """Map db_table → app_label for schema checks."""
    mapping: dict[str, str] = {}
    for label in REQUIRED_MODELS:
        model = apps.get_model(label)
        mapping[model._meta.db_table] = model._meta.app_label
    return mapping


def _missing_tables() -> list[str]:
    existing = set(connection.introspection.table_names())
    return [table for table in _required_tables() if table not in existing]


class Command(BaseCommand):
    help = (
        'Run migrations and verify required tables exist. '
        'If tables are missing while migration history says they were applied, '
        'reset that history for the affected apps and re-apply.'
    )

    def handle(self, *args, **options):
        self.stdout.write('Running migrate...')
        call_command('migrate', interactive=False, verbosity=1)

        missing = _missing_tables()
        if not missing:
            self.stdout.write(self.style.SUCCESS('Schema OK — required tables present.'))
            return

        table_to_app = _required_tables()
        apps_to_reset = sorted({table_to_app[t] for t in missing})
        self.stdout.write(
            self.style.WARNING(
                f'Missing tables after migrate: {", ".join(missing)}. '
                f'Resetting migration history for: {", ".join(apps_to_reset)} '
                'and re-applying (inconsistent volume / fake-applied state).'
            )
        )

        recorder = MigrationRecorder(connection)
        deleted, _ = recorder.migration_qs.filter(app__in=apps_to_reset).delete()
        self.stdout.write(f'Removed {deleted} migration history row(s).')

        call_command('migrate', interactive=False, verbosity=1)

        still_missing = _missing_tables()
        if still_missing:
            raise CommandError(
                'Required tables still missing after re-migrate: '
                f'{", ".join(still_missing)}. '
                'Confirm the image contains app migration files '
                '(e.g. core/migrations/0001_initial.py), then rebuild. '
                'If the MySQL volume is corrupt, reset it with: '
                'docker compose down -v  (DESTROYS DB DATA).'
            )

        self.stdout.write(self.style.SUCCESS('Schema recovered — required tables present.'))

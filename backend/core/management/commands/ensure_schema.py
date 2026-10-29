"""Apply migrations and verify every model table exists."""

from __future__ import annotations

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder


def _model_tables() -> dict[str, str]:
    """Map every managed model table, including implicit many-to-many tables, to its app."""
    mapping: dict[str, str] = {}
    for model in apps.get_models(include_auto_created=True):
        meta = model._meta
        if meta.proxy or not meta.managed:
            continue
        mapping[meta.db_table] = meta.app_label
    return mapping


def _missing_tables() -> list[str]:
    existing = set(connection.introspection.table_names())
    return sorted(table for table in _model_tables() if table not in existing)


def _unapplied_migrations() -> list[str]:
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    return [f'{migration.app_label}.{migration.name}' for migration, _backwards in plan]


def _assert_models_match_migrations() -> None:
    try:
        call_command(
            'makemigrations',
            check_changes=True,
            dry_run=True,
            interactive=False,
            verbosity=0,
        )
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise CommandError(
                'Model changes are not covered by migration files. '
                'Run ./deploy.sh so it can create them before the image is built, '
                'then commit the new backend/*/migrations/*.py files.'
            ) from exc


def _assert_ready() -> None:
    missing = _missing_tables()
    if missing:
        raise CommandError(
            'Model tables are missing: '
            f'{", ".join(missing)}. '
            'If this persists, confirm the image contains the migration files '
            'and consider resetting a corrupt MySQL volume with '
            'docker compose down -v (DESTROYS DB DATA).'
        )
    unapplied = _unapplied_migrations()
    if unapplied:
        raise CommandError(
            'Migrations are not fully applied: ' + ', '.join(unapplied) + '.'
        )
    _assert_models_match_migrations()


class Command(BaseCommand):
    help = (
        'Apply migrations and verify every model table exists. '
        'If tables are missing while migration history says they were applied, '
        'reset that history for the affected apps and re-apply.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help=(
                'Check that migrations are fully applied and every model table '
                'exists, without changing the database.'
            ),
        )

    def handle(self, *args, **options):
        if not options['verify_only']:
            self.stdout.write('Running migrate...')
            call_command('migrate', interactive=False, verbosity=1)
            missing = _missing_tables()
            if missing:
                self._recover(missing)
        _assert_ready()
        self.stdout.write(
            self.style.SUCCESS(
                'Schema OK — migrations applied and model tables present.'
            )
        )

    def _recover(self, missing: list[str]) -> None:
        table_to_app = _model_tables()
        apps_to_reset = sorted({table_to_app[table] for table in missing})
        self.stdout.write(
            self.style.WARNING(
                f'Missing tables after migrate: {", ".join(missing)}. '
                f'Resetting migration history for: {", ".join(apps_to_reset)} '
                'and re-applying (inconsistent volume / fake-applied state).'
            )
        )
        recorder = MigrationRecorder(connection)
        deleted, _detail = recorder.migration_qs.filter(app__in=apps_to_reset).delete()
        self.stdout.write(f'Removed {deleted} migration history row(s).')
        call_command('migrate', interactive=False, verbosity=1)

# Generated manually: state-only move of Lokasi from core (table core_lokasi already exists).

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Lokasi',
                    fields=[
                        ('id', models.CharField(max_length=2, primary_key=True, serialize=False)),
                        ('nama', models.CharField(max_length=128)),
                    ],
                    options={
                        'verbose_name_plural': 'Lokasi',
                        'db_table': 'core_lokasi',
                    },
                ),
            ],
            database_operations=[],
        ),
    ]

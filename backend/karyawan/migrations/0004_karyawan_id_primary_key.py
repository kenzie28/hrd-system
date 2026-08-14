# Remap Karyawan PK from autoincrement ``id`` to the business ``karyawan_id``.

from django.db import migrations, models


FK_COLUMNS = [
    ('absensi_absensi', 'karyawan_id', False),
    ('cuti_permohonancuti', 'karyawan_id', False),
    ('cuti_permohonancuti', 'supervisor_id', True),
    ('cuti_permohonancuti', 'hrd_approver_id', True),
    ('lembur_permohonanlembur', 'karyawan_id', False),
    ('lembur_permohonanlembur', 'supervisor_id', True),
    ('lembur_permohonanlembur', 'hrd_approver_id', True),
    ('gaji_gajitemp', 'karyawan_id', False),
]


def _q(schema_editor, name):
    return schema_editor.quote_name(name)


def remap_karyawan_primary_key(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'mysql':
        _remap_mysql(schema_editor)
    elif vendor == 'sqlite':
        _remap_sqlite(schema_editor)
    else:
        raise RuntimeError(
            f'Cannot remap Karyawan PK on unsupported database vendor: {vendor}'
        )


def _mysql_fk_names(cursor, table, column):
    cursor.execute(
        """
        SELECT CONSTRAINT_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
          AND REFERENCED_TABLE_NAME IS NOT NULL
        """,
        [table, column],
    )
    return [row[0] for row in cursor.fetchall()]


def _mysql_index_names(cursor, table, column):
    cursor.execute(
        """
        SELECT DISTINCT INDEX_NAME
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
          AND INDEX_NAME != 'PRIMARY'
        """,
        [table, column],
    )
    return [row[0] for row in cursor.fetchall()]


def _remap_mysql(schema_editor):
    q = lambda name: _q(schema_editor, name)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0')

        for table, column, nullable in FK_COLUMNS:
            new_col = f'{column}_new'
            cursor.execute(
                f'ALTER TABLE {q(table)} ADD COLUMN {q(new_col)} VARCHAR(7) NULL'
            )
            cursor.execute(
                f'''
                UPDATE {q(table)} t
                LEFT JOIN {q('karyawan_karyawan')} k ON t.{q(column)} = k.{q('id')}
                SET t.{q(new_col)} = k.{q('karyawan_id')}
                '''
            )
            for fk_name in _mysql_fk_names(cursor, table, column):
                cursor.execute(
                    f'ALTER TABLE {q(table)} DROP FOREIGN KEY {q(fk_name)}'
                )
            for index_name in _mysql_index_names(cursor, table, column):
                try:
                    cursor.execute(
                        f'ALTER TABLE {q(table)} DROP INDEX {q(index_name)}'
                    )
                except Exception:
                    pass
            cursor.execute(f'ALTER TABLE {q(table)} DROP COLUMN {q(column)}')
            null_sql = 'NULL' if nullable else 'NOT NULL'
            cursor.execute(
                f'ALTER TABLE {q(table)} CHANGE {q(new_col)} {q(column)} '
                f'VARCHAR(7) {null_sql}'
            )

        for index_name in _mysql_index_names(cursor, 'karyawan_karyawan', 'karyawan_id'):
            try:
                cursor.execute(
                    f'ALTER TABLE {q("karyawan_karyawan")} DROP INDEX {q(index_name)}'
                )
            except Exception:
                pass
        cursor.execute(f'ALTER TABLE {q("karyawan_karyawan")} DROP PRIMARY KEY')
        cursor.execute(f'ALTER TABLE {q("karyawan_karyawan")} DROP COLUMN {q("id")}')
        cursor.execute(
            f'ALTER TABLE {q("karyawan_karyawan")} ADD PRIMARY KEY ({q("karyawan_id")})'
        )

        for table, column, _nullable in FK_COLUMNS:
            cursor.execute(
                f'''
                ALTER TABLE {q(table)}
                ADD CONSTRAINT {q(f'{table}_{column}_fk')}
                FOREIGN KEY ({q(column)})
                REFERENCES {q('karyawan_karyawan')} ({q('karyawan_id')})
                '''
            )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'gaji_gajitemp'
              AND CONSTRAINT_NAME = 'unique_gaji_temp_per_periode'
            """
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                f'''
                ALTER TABLE {q('gaji_gajitemp')}
                ADD CONSTRAINT {q('unique_gaji_temp_per_periode')}
                UNIQUE ({q('karyawan_id')}, {q('periode')})
                '''
            )
        cursor.execute('SET FOREIGN_KEY_CHECKS = 1')


def _remap_sqlite(schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = OFF')

        cursor.execute(
            '''
            CREATE TABLE absensi_absensi_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal DATE NOT NULL,
                jam_masuk TIME NOT NULL,
                durasi BIGINT NOT NULL,
                karyawan_id VARCHAR(7) NOT NULL,
                lokasi_id VARCHAR(2) NOT NULL
            )
            '''
        )
        cursor.execute(
            '''
            INSERT INTO absensi_absensi_new
                (id, tanggal, jam_masuk, durasi, karyawan_id, lokasi_id)
            SELECT a.id, a.tanggal, a.jam_masuk, a.durasi, k.karyawan_id, a.lokasi_id
            FROM absensi_absensi a
            JOIN karyawan_karyawan k ON a.karyawan_id = k.id
            '''
        )
        cursor.execute('DROP TABLE absensi_absensi')
        cursor.execute('ALTER TABLE absensi_absensi_new RENAME TO absensi_absensi')

        cursor.execute(
            '''
            CREATE TABLE cuti_permohonancuti_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipe VARCHAR(32) NOT NULL,
                alasan TEXT NOT NULL,
                tanggal_mulai DATE NOT NULL,
                tanggal_selesai DATE NOT NULL,
                status VARCHAR(32) NOT NULL,
                karyawan_id VARCHAR(7) NOT NULL,
                supervisor_id VARCHAR(7) NULL,
                hrd_approver_id VARCHAR(7) NULL
            )
            '''
        )
        cursor.execute(
            '''
            INSERT INTO cuti_permohonancuti_new
                (id, tipe, alasan, tanggal_mulai, tanggal_selesai, status,
                 karyawan_id, supervisor_id, hrd_approver_id)
            SELECT p.id, p.tipe, p.alasan, p.tanggal_mulai, p.tanggal_selesai, p.status,
                   k.karyawan_id, s.karyawan_id, h.karyawan_id
            FROM cuti_permohonancuti p
            JOIN karyawan_karyawan k ON p.karyawan_id = k.id
            LEFT JOIN karyawan_karyawan s ON p.supervisor_id = s.id
            LEFT JOIN karyawan_karyawan h ON p.hrd_approver_id = h.id
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE cuti_cuti_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal DATE NOT NULL,
                permohonan_id BIGINT NOT NULL
            )
            '''
        )
        cursor.execute(
            '''
            INSERT INTO cuti_cuti_new (id, tanggal, permohonan_id)
            SELECT id, tanggal, permohonan_id FROM cuti_cuti
            '''
        )
        cursor.execute('DROP TABLE cuti_cuti')
        cursor.execute('DROP TABLE cuti_permohonancuti')
        cursor.execute(
            'ALTER TABLE cuti_permohonancuti_new RENAME TO cuti_permohonancuti'
        )
        cursor.execute('ALTER TABLE cuti_cuti_new RENAME TO cuti_cuti')

        cursor.execute(
            '''
            CREATE TABLE lembur_permohonanlembur_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alasan TEXT NOT NULL,
                tanggal DATE NOT NULL,
                status VARCHAR(32) NOT NULL,
                karyawan_id VARCHAR(7) NOT NULL,
                supervisor_id VARCHAR(7) NULL,
                hrd_approver_id VARCHAR(7) NULL
            )
            '''
        )
        cursor.execute(
            '''
            INSERT INTO lembur_permohonanlembur_new
                (id, alasan, tanggal, status, karyawan_id, supervisor_id, hrd_approver_id)
            SELECT p.id, p.alasan, p.tanggal, p.status,
                   k.karyawan_id, s.karyawan_id, h.karyawan_id
            FROM lembur_permohonanlembur p
            JOIN karyawan_karyawan k ON p.karyawan_id = k.id
            LEFT JOIN karyawan_karyawan s ON p.supervisor_id = s.id
            LEFT JOIN karyawan_karyawan h ON p.hrd_approver_id = h.id
            '''
        )
        cursor.execute('DROP TABLE lembur_permohonanlembur')
        cursor.execute(
            'ALTER TABLE lembur_permohonanlembur_new RENAME TO lembur_permohonanlembur'
        )

        cursor.execute(
            '''
            CREATE TABLE gaji_gajitemp_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                periode DATE NOT NULL,
                hadir VARCHAR(32) NOT NULL,
                total_hadir INTEGER NOT NULL,
                hari_sakit INTEGER NOT NULL,
                hari_cuti INTEGER NOT NULL,
                hari_cuti_tambahan INTEGER NOT NULL,
                freq_pencapaian_target INTEGER NOT NULL,
                rate_target INTEGER NOT NULL,
                rate_non_target INTEGER NOT NULL,
                gaji_pokok INTEGER NOT NULL,
                rate_uang_makan INTEGER NOT NULL,
                freq_lembur_6_jam DECIMAL(8, 2) NOT NULL,
                rate_lembur_6_jam INTEGER NOT NULL,
                freq_hari_raya INTEGER NOT NULL,
                tunjangan_lama_kerja INTEGER NOT NULL,
                tunjangan_obat INTEGER NOT NULL,
                freq_alpa INTEGER NOT NULL,
                pot_bpjs_jht INTEGER NOT NULL,
                pot_bpjs_jp INTEGER NOT NULL,
                pot_bpjs_kesehatan INTEGER NOT NULL,
                pot_pph21 INTEGER NOT NULL,
                pot_kehilangan INTEGER NOT NULL,
                koreksi_absensi INTEGER NOT NULL,
                total_gaji INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                karyawan_id VARCHAR(7) NOT NULL
            )
            '''
        )
        cursor.execute(
            '''
            INSERT INTO gaji_gajitemp_new (
                id, periode, hadir, total_hadir, hari_sakit, hari_cuti,
                hari_cuti_tambahan, freq_pencapaian_target, rate_target,
                rate_non_target, gaji_pokok, rate_uang_makan, freq_lembur_6_jam,
                rate_lembur_6_jam, freq_hari_raya, tunjangan_lama_kerja,
                tunjangan_obat, freq_alpa, pot_bpjs_jht, pot_bpjs_jp,
                pot_bpjs_kesehatan, pot_pph21, pot_kehilangan, koreksi_absensi,
                total_gaji, created_at, updated_at, karyawan_id
            )
            SELECT g.id, g.periode, g.hadir, g.total_hadir, g.hari_sakit, g.hari_cuti,
                   g.hari_cuti_tambahan, g.freq_pencapaian_target, g.rate_target,
                   g.rate_non_target, g.gaji_pokok, g.rate_uang_makan, g.freq_lembur_6_jam,
                   g.rate_lembur_6_jam, g.freq_hari_raya, g.tunjangan_lama_kerja,
                   g.tunjangan_obat, g.freq_alpa, g.pot_bpjs_jht, g.pot_bpjs_jp,
                   g.pot_bpjs_kesehatan, g.pot_pph21, g.pot_kehilangan, g.koreksi_absensi,
                   g.total_gaji, g.created_at, g.updated_at, k.karyawan_id
            FROM gaji_gajitemp g
            JOIN karyawan_karyawan k ON g.karyawan_id = k.id
            '''
        )
        cursor.execute('DROP TABLE gaji_gajitemp')
        cursor.execute('ALTER TABLE gaji_gajitemp_new RENAME TO gaji_gajitemp')
        cursor.execute(
            '''
            CREATE UNIQUE INDEX unique_gaji_temp_per_periode
            ON gaji_gajitemp (karyawan_id, periode)
            '''
        )

        cursor.execute(
            '''
            CREATE TABLE karyawan_karyawan_new (
                karyawan_id VARCHAR(7) NOT NULL PRIMARY KEY,
                nama VARCHAR(128) NOT NULL,
                jabatan VARCHAR(128) NOT NULL,
                wilayah VARCHAR(3) NOT NULL,
                "level" SMALLINT NOT NULL,
                must_change_password BOOL NOT NULL,
                lokasi_kerja_id VARCHAR(2) NULL,
                user_id INTEGER NULL UNIQUE,
                cuti_tahunan SMALLINT NOT NULL
            )
            '''
        )
        cursor.execute(
            '''
            INSERT INTO karyawan_karyawan_new (
                karyawan_id, nama, jabatan, wilayah, "level",
                must_change_password, lokasi_kerja_id, user_id, cuti_tahunan
            )
            SELECT karyawan_id, nama, jabatan, wilayah, "level",
                   must_change_password, lokasi_kerja_id, user_id, cuti_tahunan
            FROM karyawan_karyawan
            '''
        )
        cursor.execute('DROP TABLE karyawan_karyawan')
        cursor.execute('ALTER TABLE karyawan_karyawan_new RENAME TO karyawan_karyawan')
        cursor.execute('PRAGMA foreign_keys = ON')


class Migration(migrations.Migration):
    dependencies = [
        ('absensi', '0002_alter_absensi_lokasi'),
        ('cuti', '0001_initial'),
        ('gaji', '0001_initial'),
        ('karyawan', '0003_alter_karyawan_lokasi_kerja'),
        ('lembur', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remap_karyawan_primary_key, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='karyawan',
                    name='id',
                ),
                migrations.AlterField(
                    model_name='karyawan',
                    name='karyawan_id',
                    field=models.CharField(
                        max_length=7, primary_key=True, serialize=False
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]

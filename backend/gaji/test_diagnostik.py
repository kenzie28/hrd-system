import io
from datetime import date

from django.test import TestCase
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from gaji.access import GAJI_PASSWORD
from gaji.diagnostik import (
    SHEET_DIAGNOSTIK,
    SHEET_KONSTANTA,
    SHEET_TER,
    TER_NO_CEILING,
)
from gaji.lembur_bayar import (
    UPAH_HARI_LEMBUR,
    UPAH_JAM_LEMBUR_DENOMINATOR,
    UPAH_JAM_LEMBUR_NUMERATOR,
)
from gaji.services import (
    _BPJS_OF_BASE,
    _JP_AGE_CUTOFF,
    TUNJANGAN_DINAS_PER_HARI,
    write_gaji,
)
from gaji.ter import TER_BRACKETS
from karyawan.models import Karyawan, StatusKTk

URL = '/api/admin/gaji/export-diagnostik/'


class GajiDiagnostikExportTests(TestCase):
    def setUp(self):
        self.admin = Karyawan.objects.create(
            karyawan_id='0000003', nama='Admin', level=8
        )
        self.admin.refresh_from_db()
        self.employee = Karyawan.objects.create(
            karyawan_id='1000001',
            nama='Budi',
            level=3,
            base_gaji=4_500_000,
            gaji_bulanan=6_000_000,
            status_k_tk=StatusKTk.TK,
            no_bpjs='1234567890123456',
            tanggal_lahir=date(1990, 5, 1),
        )
        self.periode = date(2026, 11, 1)
        self.token = Token.objects.create(user=self.admin.user)
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
            HTTP_X_GAJI_PASSWORD=GAJI_PASSWORD,
        )

    def _download(self):
        write_gaji(self.admin, self.periode)
        write_gaji(self.employee, self.periode)
        response = self.client.get(URL, {'bulan': '2026-11'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'gaji-diagnostik-2026-11.xlsx', response['Content-Disposition']
        )
        return load_workbook(io.BytesIO(response.content))

    def _row_by_id(self, ws, karyawan_id):
        headers = [cell.value for cell in ws[1]]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] == karyawan_id:
                return dict(zip(headers, row))
        self.fail(f'no row for {karyawan_id}')

    def test_requires_gaji_password(self):
        write_gaji(self.employee, self.periode)
        locked = APIClient()
        locked.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.assertEqual(locked.get(URL, {'bulan': '2026-11'}).status_code, 403)

    def test_bad_month_and_empty_month(self):
        self.assertEqual(self.client.get(URL, {'bulan': 'nope'}).status_code, 400)
        missing = self.client.get(URL, {'bulan': '2026-11'})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()['detail'], 'Belum ada gaji untuk bulan ini.')

    def test_one_row_per_gaji_with_inputs_and_formulas(self):
        wb = self._download()
        ws = wb[SHEET_DIAGNOSTIK]
        self.assertEqual(ws.max_row, 3)

        row = self._row_by_id(ws, '1000001')
        self.assertEqual(row['nama'], 'Budi')
        self.assertEqual(row['periode'], '2026-11')
        self.assertEqual(row['ter_status'], 'A')
        self.assertEqual(row['has_bpjs'], 1)
        self.assertEqual(row['umur'], 36)
        self.assertEqual(row['base_gaji_bpjs'], 4_500_000)
        self.assertEqual(row['gaji_bulanan'], 6_000_000)
        self.assertEqual(row['gaji_tambahan'], 0)
        self.assertIsNone(row['bca_transfer'])
        self.assertNotIn('gaji_tambahan', row['net_exact'])
        self.assertNotIn('gaji_tambahan', row['total_exact'])
        self.assertNotIn('bca_transfer', row['total_gaji'])

        admin = self._row_by_id(ws, '0000003')
        self.assertEqual(admin['has_bpjs'], 0)
        self.assertIsNone(admin['umur'])

        for key in (
            'pot_alpa_exact',
            'net_exact',
            'ter_fraction',
            'pph_exact',
            'total_exact',
            'net_penghasilan',
            'persentase_pph21',
            'pot_pph21',
            'total_gaji',
        ):
            self.assertTrue(str(row[key]).startswith('='), key)
        self.assertIn('SUMPRODUCT', row['ter_fraction'])
        self.assertTrue(str(row['gaji_lembur_exact']).startswith('=IF('))
        self.assertIn(SHEET_KONSTANTA, row['gaji_lembur_exact'])
        self.assertIn('MAX(0,', row['total_gaji'])
        headers = [cell.value for cell in ws[1]]
        budi_row = next(
            index
            for index in range(2, ws.max_row + 1)
            if ws.cell(index, 1).value == '1000001'
        )
        total_exact = ws.cell(
            budi_row, headers.index('total_exact') + 1
        ).value
        for field in (
            'pot_bpjs_jht_exact',
            'pot_bpjs_jp_exact',
            'pot_bpjs_kesehatan_exact',
        ):
            ref = f'{get_column_letter(headers.index(field) + 1)}{budi_row}'
            self.assertIn(ref, total_exact)

    def test_every_bpjs_field_has_exact_and_rounded_formula(self):
        ws = self._download()[SHEET_DIAGNOSTIK]
        headers = [cell.value for cell in ws[1]]
        row = self._row_by_id(ws, '1000001')
        for field, _rate in _BPJS_OF_BASE:
            self.assertIn(f'{field}_exact', headers)
            self.assertIn(field, headers)
            self.assertIn(SHEET_KONSTANTA, row[f'{field}_exact'])
            self.assertTrue(row[field].startswith('=ROUND('))

    def test_constants_and_ter_sheets_match_code(self):
        wb = self._download()
        konstanta = {
            name: value
            for name, value in wb[SHEET_KONSTANTA].iter_rows(
                min_row=2, values_only=True
            )
        }
        self.assertEqual(
            konstanta['TUNJANGAN_DINAS_PER_HARI'], TUNJANGAN_DINAS_PER_HARI
        )
        self.assertEqual(konstanta['JP_AGE_CUTOFF'], _JP_AGE_CUTOFF)
        self.assertEqual(
            konstanta['UPAH_JAM_LEMBUR_NUMERATOR'], UPAH_JAM_LEMBUR_NUMERATOR
        )
        self.assertEqual(
            konstanta['UPAH_JAM_LEMBUR_DENOMINATOR'], UPAH_JAM_LEMBUR_DENOMINATOR
        )
        self.assertEqual(konstanta['UPAH_HARI_LEMBUR'], UPAH_HARI_LEMBUR)
        for field, rate in _BPJS_OF_BASE:
            self.assertAlmostEqual(konstanta[f'rate_{field}'], float(rate))

        ter_rows = list(wb[SHEET_TER].iter_rows(min_row=2, values_only=True))
        expected = [
            (cat, lo, TER_NO_CEILING if hi is None else hi, float(rate))
            for cat, brackets in TER_BRACKETS.items()
            for lo, hi, rate in brackets
        ]
        self.assertEqual(len(ter_rows), len(expected))
        for got, want in zip(ter_rows, expected):
            self.assertEqual(got[:3], want[:3])
            self.assertAlmostEqual(got[3], want[3])

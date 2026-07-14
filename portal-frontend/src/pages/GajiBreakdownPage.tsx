import type { ReactNode } from 'react'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { Button, Divider, Empty, Spin, Typography } from 'antd'
import dayjs from 'dayjs'
import { useNavigate, useParams } from 'react-router-dom'
import { useGaji } from '../api/gaji'
import type { GajiDetail } from '../api/types'
import { formatCurrency } from '../constants'

type RowSpec = {
  label: string
  value: number | string
  isCurrency?: boolean
}

function isVisibleRow({ value }: RowSpec): boolean {
  if (typeof value === 'string') return /\d/.test(value)
  return value !== 0
}

function Row({ label, value, isCurrency = true }: RowSpec) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
      <Typography.Text type="secondary">{label}</Typography.Text>
      <Typography.Text>
        {typeof value === 'string' || !isCurrency ? value : formatCurrency(value)}
      </Typography.Text>
    </div>
  )
}

function buildSection(rows: RowSpec[]): ReactNode | null {
  const visible = rows.filter(isVisibleRow)
  if (visible.length === 0) return null
  return (
    <div style={{ padding: '4px 0' }}>
      {visible.map((row) => (
        <Row key={row.label} {...row} />
      ))}
    </div>
  )
}

function GajiBreakdown({ gaji }: { gaji: GajiDetail }) {
  const sections = [
    buildSection([
      { label: 'Hadir', value: gaji.hadir, isCurrency: false },
      { label: 'Total Hadir', value: gaji.total_hadir, isCurrency: false },
      { label: 'Hari Sakit', value: gaji.hari_sakit, isCurrency: false },
      { label: 'Hari Cuti', value: gaji.hari_cuti, isCurrency: false },
      { label: 'Hari Cuti Tambahan', value: gaji.hari_cuti_tambahan, isCurrency: false },
    ]),
    buildSection([
      {
        label: 'Frequency Pencapaian Target',
        value: gaji.freq_pencapaian_target,
        isCurrency: false,
      },
      { label: 'Rate Target', value: gaji.rate_target },
      { label: 'Nominal dari Target', value: gaji.nominal_target },
      {
        label: 'Frequency Hari Non-Target',
        value: gaji.freq_hari_non_target,
        isCurrency: false,
      },
      { label: 'Rate Non-Target', value: gaji.rate_non_target },
      { label: 'Nominal dari Non-Target', value: gaji.nominal_non_target },
      { label: 'Gaji Pokok', value: gaji.gaji_pokok },
    ]),
    buildSection([
      ...(gaji.rate_uang_makan !== 0
        ? [{ label: 'Frequency Hadir', value: gaji.total_hadir, isCurrency: false }]
        : []),
      { label: 'Rate Uang Makan', value: gaji.rate_uang_makan },
      { label: 'Nominal dari Uang Makan', value: gaji.nominal_uang_makan },
    ]),
    buildSection([
      {
        label: 'Frequency Lembur /6 Jam',
        value: Number(gaji.freq_lembur_6_jam),
        isCurrency: false,
      },
      { label: 'Rate Lembur /6 Jam', value: gaji.rate_lembur_6_jam },
      { label: 'Nominal dari Lembur', value: gaji.nominal_lembur },
      { label: 'Frequency Hari Raya', value: gaji.freq_hari_raya, isCurrency: false },
      { label: 'Rate Hari Raya', value: gaji.rate_hari_raya },
      { label: 'Nominal dari Hari Raya', value: gaji.nominal_hari_raya },
    ]),
    buildSection([
      { label: 'Tunjangan Lama Kerja', value: gaji.tunjangan_lama_kerja },
      { label: 'Tunjangan Obat', value: gaji.tunjangan_obat },
    ]),
    buildSection([
      { label: 'Frequency Alpa', value: gaji.freq_alpa, isCurrency: false },
      { label: 'Pengurang dari Alpa', value: gaji.pengurang_alpa },
    ]),
    buildSection([
      { label: 'Potongan BPJS JHT', value: gaji.pot_bpjs_jht },
      { label: 'Potongan BPJS JP', value: gaji.pot_bpjs_jp },
      { label: 'Potongan BPJS Kesehatan', value: gaji.pot_bpjs_kesehatan },
      { label: 'PPH 21', value: gaji.pot_pph21 },
      { label: 'Potongan Kehilangan', value: gaji.pot_kehilangan },
      { label: 'Koreksi Absensi', value: gaji.koreksi_absensi },
    ]),
  ].filter((section): section is ReactNode => section != null)

  return (
    <div>
      {sections.map((section, index) => (
        <div key={index}>
          {index > 0 ? <Divider style={{ margin: '4px 0' }} /> : null}
          {section}
        </div>
      ))}

      {sections.length > 0 ? <Divider style={{ margin: '4px 0' }} /> : null}

      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          Gaji Diterima
        </Typography.Title>
        <Typography.Title level={5} style={{ margin: 0 }}>
          {formatCurrency(gaji.total_gaji)}
        </Typography.Title>
      </div>
    </div>
  )
}

export default function GajiBreakdownPage() {
  const { bulan } = useParams<{ bulan: string }>()
  const navigate = useNavigate()
  const { data, isLoading } = useGaji(bulan)
  const gaji = data?.gaji ?? null

  const bulanLabel = bulan ? dayjs(bulan).format('MMMM YYYY') : ''

  return (
    <div>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        style={{ paddingLeft: 0, marginBottom: 8 }}
        onClick={() => navigate('/gaji')}
      >
        Kembali
      </Button>
      <Typography.Title level={3} style={{ marginTop: 0 }}>
        Rincian Gaji — {bulanLabel}
      </Typography.Title>

      {isLoading ? (
        <div style={{ padding: 48, textAlign: 'center' }}>
          <Spin />
        </div>
      ) : gaji ? (
        <GajiBreakdown gaji={gaji} />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Data gaji belum tersedia untuk periode ini."
        />
      )}
    </div>
  )
}

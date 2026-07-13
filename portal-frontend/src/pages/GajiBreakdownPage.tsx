import type { ReactNode } from 'react'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { Button, Divider, Empty, Spin, Typography } from 'antd'
import dayjs from 'dayjs'
import { useNavigate, useParams } from 'react-router-dom'
import { useGaji } from '../api/gaji'
import type { GajiDetail } from '../api/types'
import { formatCurrency } from '../constants'

function Row({
  label,
  value,
  isCurrency = true,
}: {
  label: string
  value: number
  isCurrency?: boolean
}) {
  if (value === 0) return null
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
      <Typography.Text type="secondary">{label}</Typography.Text>
      <Typography.Text>{isCurrency ? formatCurrency(value) : value}</Typography.Text>
    </div>
  )
}

function Group({ children }: { children: ReactNode }) {
  return <div style={{ padding: '4px 0' }}>{children}</div>
}

function GajiBreakdown({ gaji }: { gaji: GajiDetail }) {
  return (
    <div>
      <Group>
        <Row label="Hadir" value={gaji.hadir} isCurrency={false} />
        <Row label="Hari Sakit" value={gaji.hari_sakit} isCurrency={false} />
        <Row label="Hari Cuti" value={gaji.hari_cuti} isCurrency={false} />
        <Row label="Hari Cuti Tambahan" value={gaji.hari_cuti_tambahan} isCurrency={false} />
      </Group>

      <Divider style={{ margin: '4px 0' }} />

      <Group>
        <Row
          label="Frequency Pencapaian Target"
          value={gaji.freq_pencapaian_target}
          isCurrency={false}
        />
        <Row label="Rate Target" value={gaji.rate_target} />
        <Row label="Nominal dari Target" value={gaji.nominal_target} />
        <Row
          label="Frequency Hari Non-Target"
          value={gaji.freq_hari_non_target}
          isCurrency={false}
        />
        <Row label="Rate Non-Target" value={gaji.rate_non_target} />
        <Row label="Nominal dari Non-Target" value={gaji.nominal_non_target} />
        <Row label="Gaji Pokok" value={gaji.gaji_pokok} />
      </Group>

      <Divider style={{ margin: '4px 0' }} />

      <Group>
        <Row label="Frequency Hadir" value={gaji.hadir} isCurrency={false} />
        <Row label="Rate Uang Makan" value={gaji.rate_uang_makan} />
        <Row label="Nominal dari Uang Makan" value={gaji.nominal_uang_makan} />
      </Group>

      <Divider style={{ margin: '4px 0' }} />

      <Group>
        <Row
          label="Frequency Lembur /6 Jam"
          value={Number(gaji.freq_lembur_6_jam)}
          isCurrency={false}
        />
        <Row label="Rate Lembur /6 Jam" value={gaji.rate_lembur_6_jam} />
        <Row label="Nominal dari Lembur" value={gaji.nominal_lembur} />
        <Row label="Frequency Hari Raya" value={gaji.freq_hari_raya} isCurrency={false} />
        <Row label="Rate Hari Raya" value={gaji.rate_hari_raya} />
        <Row label="Nominal dari Hari Raya" value={gaji.nominal_hari_raya} />
      </Group>

      <Divider style={{ margin: '4px 0' }} />

      <Group>
        <Row label="Tunjangan Lama Kerja" value={gaji.tunjangan_lama_kerja} />
        <Row label="Tunjangan Obat" value={gaji.tunjangan_obat} />
      </Group>

      <Divider style={{ margin: '4px 0' }} />

      <Group>
        <Row label="Frequency Alpa" value={gaji.freq_alpa} isCurrency={false} />
        <Row label="Pengurang dari Alpa" value={gaji.pengurang_alpa} />
      </Group>

      <Divider style={{ margin: '4px 0' }} />

      <Group>
        <Row label="Potongan BPJS JHT" value={gaji.pot_bpjs_jht} />
        <Row label="Potongan BPJS JP" value={gaji.pot_bpjs_jp} />
        <Row label="Potongan BPJS Kesehatan" value={gaji.pot_bpjs_kesehatan} />
        <Row label="PPH 21" value={gaji.pot_pph21} />
        <Row label="Potongan Kehilangan" value={gaji.pot_kehilangan} />
        <Row label="Koreksi Absensi" value={gaji.koreksi_absensi} />
      </Group>

      <Divider style={{ margin: '4px 0' }} />

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

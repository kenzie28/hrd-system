import { useState } from 'react'
import { Tag } from 'antd'
import dayjs from 'dayjs'
import { useCuti } from '../api/hooks'
import type { Cuti } from '../api/types'
import { ViewModeToggle } from '../components/ViewModeToggle'
import { CUTI_TIPE_COLORS } from '../constants'

export function CutiTab() {
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<number>()
  const { data: cuti, isLoading } = useCuti({
    karyawan: karyawanId,
    bulan: month.format('YYYY-MM'),
  })

  return (
    <ViewModeToggle<Cuti>
      data={cuti ?? []}
      loading={isLoading}
      karyawanId={karyawanId}
      onKaryawanChange={setKaryawanId}
      month={month}
      onMonthChange={setMonth}
      getDate={(c) => c.tanggal}
      columns={[
        {
          title: 'Tanggal',
          dataIndex: 'tanggal',
          sorter: (a, b) => a.tanggal.localeCompare(b.tanggal),
        },
        { title: 'Karyawan', dataIndex: 'karyawan_nama' },
        {
          title: 'Tipe',
          render: (_, c) => <Tag color={CUTI_TIPE_COLORS[c.tipe]}>{c.tipe_display}</Tag>,
        },
        { title: 'Permohonan', dataIndex: 'permohonan', width: 110 },
        { title: 'Supervisor', dataIndex: 'supervisor_nama', render: (s: string | null) => s ?? '-' },
      ]}
      renderBadge={(c) => (
        <Tag
          color={CUTI_TIPE_COLORS[c.tipe]}
          style={{ fontSize: 11, lineHeight: '16px', margin: 0 }}
        >
          {c.karyawan_nama.split(' ')[0]}: {c.tipe_display}
        </Tag>
      )}
    />
  )
}

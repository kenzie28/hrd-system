import { useState } from 'react'
import { Tag } from 'antd'
import dayjs from 'dayjs'
import { useLembur } from '../api/hooks'
import type { PermohonanLembur } from '../api/types'
import { ViewModeToggle } from '../components/ViewModeToggle'

export function LemburTab() {
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<string>()
  const { data: lembur, isLoading } = useLembur({
    karyawan_id: karyawanId,
    bulan: month.format('YYYY-MM'),
  })

  return (
    <ViewModeToggle<PermohonanLembur>
      data={lembur ?? []}
      loading={isLoading}
      karyawanId={karyawanId}
      onKaryawanChange={setKaryawanId}
      month={month}
      onMonthChange={setMonth}
      getDate={(r) => r.tanggal}
      columns={[
        {
          title: 'Tanggal',
          dataIndex: 'tanggal',
          sorter: (a, b) => a.tanggal.localeCompare(b.tanggal),
        },
        { title: 'ID Karyawan', dataIndex: 'karyawan_id', width: 110 },
        { title: 'Karyawan', dataIndex: 'karyawan_nama' },
        {
          title: 'Alasan',
          dataIndex: 'alasan',
          render: (v: string) => v || '-',
        },
        {
          title: 'Supervisor',
          dataIndex: 'supervisor_nama',
          render: (s: string | null) => s ?? '-',
        },
        {
          title: 'HRD',
          dataIndex: 'hrd_approver_nama',
          render: (s: string | null) => s ?? '-',
        },
      ]}
      renderBadge={(r) => (
        <Tag color="green" style={{ fontSize: 11, lineHeight: '16px', margin: 0 }}>
          {r.karyawan_nama.split(' ')[0]}: Lembur
        </Tag>
      )}
    />
  )
}

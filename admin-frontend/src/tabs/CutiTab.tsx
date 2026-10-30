import { useState } from 'react'
import { Tag } from 'antd'
import dayjs from 'dayjs'
import { useCuti } from '../api/hooks'
import type { Cuti } from '../api/types'
import { ViewModeToggle } from '../components/ViewModeToggle'
import { CUTI_TIPE_COLORS } from '../constants'

function tipeText(c: Cuti) {
  if (c.tipe === 'CUTI_TAHUNAN' && c.sisa_cuti_tahunan != null) {
    return `${c.tipe_display} (Sisa: ${c.sisa_cuti_tahunan} hari)`
  }
  return c.tipe_display
}

export function CutiTab() {
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<string>()
  const { data: cuti, isLoading } = useCuti({
    karyawan_id: karyawanId,
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
          defaultSortOrder: 'descend',
        },
        { title: 'Karyawan', dataIndex: 'karyawan_nama' },
        {
          title: 'Tipe',
          render: (_, c) => <Tag color={CUTI_TIPE_COLORS[c.tipe]}>{tipeText(c)}</Tag>,
        },
        { title: 'Supervisor', dataIndex: 'supervisor_nama', render: (s: string | null) => s ?? '-' },
      ]}
      renderBadge={(c) => (
        <Tag
          color={CUTI_TIPE_COLORS[c.tipe]}
          style={{ fontSize: 11, lineHeight: '16px', margin: 0 }}
        >
          {c.karyawan_nama.split(' ')[0]}: {tipeText(c)}
        </Tag>
      )}
    />
  )
}

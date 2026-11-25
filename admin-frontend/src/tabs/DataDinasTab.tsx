import { useState } from 'react'
import { App as AntApp, Button, Popconfirm, Tag } from 'antd'
import dayjs from 'dayjs'
import { useDeleteDinas, useDinas } from '../api/hooks'
import type { Dinas } from '../api/types'
import { ViewModeToggle } from '../components/ViewModeToggle'

export function DataDinasTab() {
  const { message } = AntApp.useApp()
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<string>()
  const { data: dinas, isLoading } = useDinas({
    karyawan_id: karyawanId,
    bulan: month.format('YYYY-MM'),
  })
  const removeDinas = useDeleteDinas()

  const onDelete = async (row: Dinas) => {
    try {
      await removeDinas.mutateAsync(row.id)
      message.success('Dinas dihapus.')
    } catch {
      message.error('Gagal menghapus dinas.')
    }
  }

  return (
    <ViewModeToggle<Dinas>
      data={dinas ?? []}
      loading={isLoading}
      karyawanId={karyawanId}
      onKaryawanChange={setKaryawanId}
      month={month}
      onMonthChange={setMonth}
      getDate={(row) => row.tanggal}
      columns={[
        {
          title: 'Tanggal',
          dataIndex: 'tanggal',
          sorter: (a, b) => a.tanggal.localeCompare(b.tanggal),
          defaultSortOrder: 'descend',
        },
        { title: 'ID Karyawan', dataIndex: 'karyawan_id', width: 110 },
        { title: 'Karyawan', dataIndex: 'karyawan_nama' },
        {
          title: 'Aksi',
          width: 110,
          render: (_, row) => (
            <Popconfirm
              title="Hapus dinas pada hari ini?"
              okText="Hapus"
              cancelText="Batal"
              onConfirm={() => onDelete(row)}
            >
              <Button size="small" danger loading={removeDinas.isPending}>
                Hapus
              </Button>
            </Popconfirm>
          ),
        },
      ]}
      renderBadge={(row) => (
        <Tag color="blue" style={{ fontSize: 11, lineHeight: '16px', margin: 0 }}>
          {row.karyawan_nama.split(' ')[0]}: Dinas
        </Tag>
      )}
    />
  )
}

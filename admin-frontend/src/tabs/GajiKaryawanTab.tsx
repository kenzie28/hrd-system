import { Alert, Table } from 'antd'
import { useGajiKaryawan } from '../api/hooks'
import type { GajiKaryawan } from '../api/types'
import { formatCurrency } from '../constants'

function blank(value: string) {
  return value.trim() ? value : '—'
}

export function GajiKaryawanTab() {
  const { data, isLoading, isError } = useGajiKaryawan()

  if (isError) {
    return <Alert type="error" showIcon message="Gagal memuat daftar karyawan." />
  }

  return (
    <Table<GajiKaryawan>
      rowKey="karyawan_id"
      size="small"
      loading={isLoading}
      dataSource={data ?? []}
      pagination={{ pageSize: 20, showSizeChanger: false }}
      scroll={{ x: true }}
      columns={[
        { title: 'ID Karyawan', dataIndex: 'karyawan_id', width: 120 },
        { title: 'Nama', dataIndex: 'nama' },
        { title: 'Level', dataIndex: 'level', width: 80 },
        {
          title: 'Jabatan',
          dataIndex: 'jabatan',
          render: (value: string) => blank(value),
        },
        {
          title: 'No. BPJS',
          dataIndex: 'no_bpjs',
          width: 180,
          render: (value: string) => blank(value),
        },
        {
          title: 'Base Gaji',
          dataIndex: 'base_gaji',
          width: 160,
          align: 'right',
          render: (value: number) => formatCurrency(value),
        },
        {
          title: 'Gaji Bulanan',
          dataIndex: 'gaji_bulanan',
          width: 160,
          align: 'right',
          render: (value: number) => formatCurrency(value),
        },
      ]}
    />
  )
}

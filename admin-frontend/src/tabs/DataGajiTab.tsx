import { useState } from 'react'
import { DatePicker, Select, Space, Table } from 'antd'
import dayjs from 'dayjs'
import { useGajiTemp, useKaryawan } from '../api/hooks'
import type { GajiTemp } from '../api/types'
import { formatCurrency } from '../constants'

export function DataGajiTab() {
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<number>()
  const { data: karyawan } = useKaryawan()
  const { data, isLoading } = useGajiTemp({
    karyawan: karyawanId,
    bulan: month.format('YYYY-MM'),
  })

  const karyawanOptions = (karyawan ?? []).map((k) => ({ label: k.nama, value: k.id }))

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Select
          placeholder="Semua karyawan"
          style={{ minWidth: 180 }}
          allowClear
          options={karyawanOptions}
          value={karyawanId}
          onChange={(value) => setKaryawanId(value ?? undefined)}
          showSearch
          optionFilterProp="label"
        />
        <DatePicker
          picker="month"
          value={month}
          onChange={(value) => value && setMonth(value)}
          allowClear={false}
        />
      </Space>

      <Table<GajiTemp>
        rowKey="id"
        size="small"
        loading={isLoading}
        dataSource={data ?? []}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: true }}
        columns={[
          { title: 'ID Karyawan', dataIndex: 'karyawan_kode', width: 110 },
          { title: 'Karyawan', dataIndex: 'karyawan_nama' },
          { title: 'Periode', dataIndex: 'periode', width: 100 },
          { title: 'Hadir', dataIndex: 'hadir', width: 80 },
          { title: 'Total Hadir', dataIndex: 'total_hadir', width: 90 },
          { title: 'Alpa', dataIndex: 'freq_alpa', width: 70 },
          {
            title: 'Gaji Pokok',
            dataIndex: 'gaji_pokok',
            render: (v: number) => formatCurrency(v),
          },
          {
            title: 'Total Gaji',
            dataIndex: 'total_gaji',
            render: (v: number) => formatCurrency(v),
          },
        ]}
      />
    </Space>
  )
}

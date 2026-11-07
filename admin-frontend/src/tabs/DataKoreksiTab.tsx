import { useState } from 'react'
import { DatePicker, Select, Space, Table } from 'antd'
import dayjs from 'dayjs'
import { useKaryawan, useKoreksi } from '../api/hooks'
import type { Koreksi } from '../api/types'
import { formatCurrency } from '../constants'

export function DataKoreksiTab() {
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<string>()
  const { data: karyawan } = useKaryawan()
  const { data, isLoading } = useKoreksi({
    karyawan_id: karyawanId,
    bulan: month.format('YYYY-MM'),
  })

  const karyawanOptions = (karyawan ?? []).map((k) => ({
    label: k.nama,
    value: k.karyawan_id,
  }))

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

      <Table<Koreksi>
        rowKey="id"
        size="small"
        loading={isLoading}
        dataSource={data ?? []}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: true }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          { title: 'ID Karyawan', dataIndex: 'karyawan_id', width: 120 },
          { title: 'Karyawan', dataIndex: 'karyawan_nama' },
          { title: 'Tipe', dataIndex: 'tipe', width: 160 },
          {
            title: 'Nominal',
            dataIndex: 'nominal',
            width: 160,
            render: (value: number) => formatCurrency(value),
          },
          { title: 'Bulan', dataIndex: 'bulan', width: 120 },
        ]}
      />
    </Space>
  )
}

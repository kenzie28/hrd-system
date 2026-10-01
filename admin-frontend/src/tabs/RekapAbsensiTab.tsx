import { useState } from 'react'
import { DatePicker, Space, Table, Typography } from 'antd'
import dayjs from 'dayjs'
import { useRekapAbsensi } from '../api/hooks'
import type { RekapAbsensi } from '../api/types'

export function RekapAbsensiTab() {
  const [month, setMonth] = useState(() => dayjs())
  const bulan = month.format('YYYY-MM')
  const { data, isLoading } = useRekapAbsensi(bulan)

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <DatePicker
        picker="month"
        value={month}
        onChange={(value) => value && setMonth(value)}
        allowClear={false}
      />

      <Table<RekapAbsensi>
        rowKey="id"
        size="small"
        loading={isLoading}
        dataSource={data ?? []}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'Belum ada rekap untuk bulan ini. Jalankan Proses Absensi.' }}
        expandable={{
          rowExpandable: (record) => record.catatan.length > 0,
          expandedRowRender: (record) => (
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {record.catatan.map((note) => (
                <li key={note.id}>
                  <Typography.Text>
                    {note.tanggal ?? '—'} — {note.pesan}
                  </Typography.Text>
                </li>
              ))}
            </ul>
          ),
        }}
        columns={[
          {
            title: 'Karyawan',
            render: (_, record) => `${record.karyawan_nama} (${record.karyawan_id})`,
          },
          { title: 'Hadir', dataIndex: 'hari_hadir', width: 80 },
          { title: 'Telat', dataIndex: 'hari_telat', width: 80 },
          { title: 'Alpa', dataIndex: 'hari_alpa', width: 80 },
          { title: 'Pulang Cepat', dataIndex: 'hari_keluar_cepat', width: 120 },
          { title: 'Menit Telat', dataIndex: 'total_menit_telat', width: 110 },
          { title: 'Menit Lembur', dataIndex: 'total_menit_lembur', width: 120 },
        ]}
      />
    </Space>
  )
}

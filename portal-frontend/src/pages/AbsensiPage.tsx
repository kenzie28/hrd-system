import { useState } from 'react'
import { DatePicker, Table, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useMyAbsensi } from '../api/absensi'
import type { Absensi } from '../api/types'
import { fmtTime } from '../constants'

export default function AbsensiPage() {
  const [bulan, setBulan] = useState<Dayjs>(() => dayjs())
  const { data, isLoading } = useMyAbsensi(bulan.format('YYYY-MM'))

  return (
    <div>
      <Typography.Title level={3}>Absensi</Typography.Title>
      <Typography.Paragraph type="secondary">
        Riwayat absensi Anda pada bulan yang dipilih.
      </Typography.Paragraph>
      <DatePicker
        picker="month"
        value={bulan}
        allowClear={false}
        onChange={(value) => value && setBulan(value)}
        style={{ marginBottom: 16 }}
      />
      <Table<Absensi>
        rowKey="id"
        loading={isLoading}
        dataSource={data ?? []}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: true }}
        locale={{ emptyText: 'Tidak ada data absensi pada bulan ini.' }}
        columns={[
          {
            title: 'Tanggal',
            dataIndex: 'tanggal',
            sorter: (a, b) => a.tanggal.localeCompare(b.tanggal),
            defaultSortOrder: 'ascend',
          },
          { title: 'Lokasi', dataIndex: 'lokasi_nama' },
          { title: 'Jam Masuk', dataIndex: 'jam_masuk', render: fmtTime },
          {
            title: 'Jam Keluar',
            render: (_, r) => (
              <>
                {fmtTime(r.jam_keluar)}
                {r.keluar_hari_offset > 0 && (
                  <sup style={{ marginLeft: 2 }}>+{r.keluar_hari_offset}</sup>
                )}
              </>
            ),
          },
          {
            title: 'Durasi',
            dataIndex: 'durasi',
            render: (d: string) => d.slice(0, 5),
          },
        ]}
      />
    </div>
  )
}

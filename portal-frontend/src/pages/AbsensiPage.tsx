import { useState } from 'react'
import { DatePicker, Table, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useMyAbsensi, useMyKehadiran } from '../api/absensi'
import type { Absensi, Kehadiran } from '../api/types'
import { fmtTime } from '../constants'

export default function AbsensiPage() {
  const [bulan, setBulan] = useState<Dayjs>(() => dayjs())
  const month = bulan.format('YYYY-MM')
  const { data: kehadiran, isLoading: kehadiranLoading } = useMyKehadiran(month)
  const { data, isLoading } = useMyAbsensi(month)

  return (
    <div>
      <Typography.Title level={3}>Absensi</Typography.Title>
      <Typography.Paragraph type="secondary">
        Kehadiran yang sudah diproses, lalu riwayat absensi mentah, untuk bulan yang dipilih.
      </Typography.Paragraph>
      <DatePicker
        picker="month"
        value={bulan}
        allowClear={false}
        onChange={(value) => value && setBulan(value)}
        style={{ marginBottom: 16 }}
      />
      <Typography.Title level={5}>Kehadiran</Typography.Title>
      <Table<Kehadiran>
        rowKey="id"
        loading={kehadiranLoading}
        dataSource={kehadiran ?? []}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: true }}
        style={{ marginBottom: 24 }}
        locale={{ emptyText: 'Belum ada kehadiran pada bulan ini.' }}
        columns={[
          {
            title: 'Tanggal',
            dataIndex: 'tanggal',
            sorter: (a, b) => a.tanggal.localeCompare(b.tanggal),
            defaultSortOrder: 'ascend',
          },
          { title: 'Status', dataIndex: 'status_display' },
          {
            title: 'Shift',
            render: (_, row) =>
              `${fmtTime(row.shift_jam_masuk)}–${fmtTime(row.shift_jam_keluar)}`,
          },
          { title: 'Menit Telat', dataIndex: 'menit_telat' },
          { title: 'Cepat Keluar', dataIndex: 'cepat_keluar' },
          { title: 'Menit Lembur', dataIndex: 'lembur' },
        ]}
      />
      <Typography.Title level={5}>Absensi</Typography.Title>
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

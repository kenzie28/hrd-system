import { useState } from 'react'
import { DatePicker, Descriptions, Modal, Table, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useMyKehadiran } from '../api/absensi'
import type { Kehadiran } from '../api/types'
import { fmtTime } from '../constants'

export default function AbsensiPage() {
  const [bulan, setBulan] = useState<Dayjs>(() => dayjs())
  const [selected, setSelected] = useState<Kehadiran | null>(null)
  const month = bulan.format('YYYY-MM')
  const { data: kehadiran, isLoading } = useMyKehadiran(month)

  return (
    <div>
      <Typography.Title level={3}>Absensi</Typography.Title>
      <Typography.Paragraph type="secondary">
        Pilih satu kehadiran untuk melihat absensi pada hari itu.
      </Typography.Paragraph>
      <DatePicker
        picker="month"
        value={bulan}
        allowClear={false}
        onChange={(value) => {
          if (!value) return
          setBulan(value)
          setSelected(null)
        }}
        style={{ marginBottom: 16 }}
      />
      <Table<Kehadiran>
        rowKey="id"
        loading={isLoading}
        dataSource={kehadiran ?? []}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: true }}
        locale={{ emptyText: 'Belum ada kehadiran pada bulan ini.' }}
        onRow={(row) => ({
          onClick: () => setSelected(row),
          style: { cursor: 'pointer' },
        })}
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
              row.shift_jam_masuk && row.shift_jam_keluar
                ? `${fmtTime(row.shift_jam_masuk)}–${fmtTime(row.shift_jam_keluar)}`
                : '—',
          },
          { title: 'Menit Telat', dataIndex: 'menit_telat' },
          { title: 'Cepat Keluar', dataIndex: 'cepat_keluar' },
          { title: 'Menit Lembur', dataIndex: 'lembur' },
        ]}
      />
      <Modal
        title={selected ? `Absensi ${selected.tanggal}` : 'Absensi'}
        open={selected != null}
        onCancel={() => setSelected(null)}
        footer={null}
        destroyOnHidden
      >
        {selected?.absensi ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="Lokasi">{selected.absensi.lokasi_nama}</Descriptions.Item>
            <Descriptions.Item label="Jam Masuk">
              {fmtTime(selected.absensi.jam_masuk)}
            </Descriptions.Item>
            <Descriptions.Item label="Jam Keluar">
              {fmtTime(selected.absensi.jam_keluar)}
              {selected.absensi.keluar_hari_offset > 0 && (
                <sup style={{ marginLeft: 2 }}>+{selected.absensi.keluar_hari_offset}</sup>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Durasi">
              {selected.absensi.durasi.slice(0, 5)}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Typography.Text>Tidak ada entri absensi yang tersedia.</Typography.Text>
        )}
      </Modal>
    </div>
  )
}

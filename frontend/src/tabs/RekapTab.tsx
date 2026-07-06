import { useState } from 'react'
import { App, Button, DatePicker, Modal, Space, Tag, Typography } from 'antd'
import { SyncOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { useRekap, useRekapProcess } from '../api/hooks'
import type { Rekap } from '../api/types'
import { ViewModeToggle } from '../components/ViewModeToggle'
import { JamKeluar } from '../components/JamKeluar'
import { REKAP_STATUS_COLORS, fmtTime } from '../constants'

export function RekapTab() {
  const { message } = App.useApp()
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<number>()
  const { data: rekap, isLoading } = useRekap({
    karyawan: karyawanId,
    bulan: month.format('YYYY-MM'),
  })
  const processMutation = useRekapProcess()

  const [processOpen, setProcessOpen] = useState(false)
  const [range, setRange] = useState<[Dayjs, Dayjs]>(() => [
    dayjs().startOf('month'),
    dayjs().endOf('month'),
  ])

  const handleProcess = async () => {
    const res = await processMutation.mutateAsync({
      tanggal_mulai: range[0].format('YYYY-MM-DD'),
      tanggal_selesai: range[1].format('YYYY-MM-DD'),
    })
    message.success(`${res.data.processed} baris rekap diproses`)
    setProcessOpen(false)
  }

  const statusTag = (r: Rekap) => (
    <Tag color={REKAP_STATUS_COLORS[r.status]}>{r.status_display}</Tag>
  )

  return (
    <>
      <ViewModeToggle<Rekap>
        data={rekap ?? []}
        loading={isLoading}
        karyawanId={karyawanId}
        onKaryawanChange={setKaryawanId}
        month={month}
        onMonthChange={setMonth}
        getDate={(r) => r.tanggal}
        toolbarExtra={
          <Button type="primary" icon={<SyncOutlined />} onClick={() => setProcessOpen(true)}>
            Proses Rekap
          </Button>
        }
        columns={[
          { title: 'Tanggal', dataIndex: 'tanggal', sorter: (a, b) => a.tanggal.localeCompare(b.tanggal) },
          { title: 'Karyawan', dataIndex: 'karyawan_nama' },
          {
            title: 'Shift',
            render: (_, r) =>
              `${fmtTime(r.jadwal_detail.shift_detail.jam_masuk)} - ${fmtTime(r.jadwal_detail.shift_detail.jam_keluar)}`,
          },
          {
            title: 'Absensi',
            render: (_, r) =>
              r.absensi_detail ? (
                <>
                  {fmtTime(r.absensi_detail.jam_masuk)} -{' '}
                  <JamKeluar
                    jamKeluar={r.absensi_detail.jam_keluar}
                    keluarHariOffset={r.absensi_detail.keluar_hari_offset}
                  />
                </>
              ) : (
                '-'
              ),
          },
          {
            title: 'Cuti',
            render: (_, r) => r.cuti_detail?.tipe_display ?? '-',
          },
          {
            title: 'Status',
            render: (_, r) => statusTag(r),
            filters: Object.entries(REKAP_STATUS_COLORS).map(([status]) => ({
              text: status,
              value: status,
            })),
            onFilter: (value, r) => r.status === value,
          },
        ]}
        renderBadge={(r) => (
          <Tag
            color={REKAP_STATUS_COLORS[r.status]}
            style={{ fontSize: 11, lineHeight: '16px', margin: 0 }}
          >
            {r.karyawan_nama.split(' ')[0]}: {r.status_display}
          </Tag>
        )}
      />

      <Modal
        title="Proses Rekap Kehadiran"
        open={processOpen}
        onOk={handleProcess}
        okText="Proses"
        confirmLoading={processMutation.isPending}
        onCancel={() => setProcessOpen(false)}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Rekap pada rentang tanggal ini akan dihapus dan dibuat ulang berdasarkan Jadwal,
            Absensi, Cuti, dan Liburan terkini.
          </Typography.Paragraph>
          <DatePicker.RangePicker
            style={{ width: '100%' }}
            value={range}
            onChange={(value) => {
              if (value?.[0] && value?.[1]) setRange([value[0], value[1]])
            }}
            allowClear={false}
            presets={[
              { label: 'Bulan ini', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
              {
                label: 'Bulan lalu',
                value: [
                  dayjs().subtract(1, 'month').startOf('month'),
                  dayjs().subtract(1, 'month').endOf('month'),
                ],
              },
            ]}
          />
        </Space>
      </Modal>
    </>
  )
}

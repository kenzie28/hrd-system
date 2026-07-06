import { useMemo, useState } from 'react'
import {
  App,
  Button,
  DatePicker,
  Form,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  TimePicker,
  Typography,
} from 'antd'
import dayjs, { Dayjs } from 'dayjs'
import { useAbsensi, useAbsensiMutations, useKaryawan, useLokasi } from '../api/hooks'
import type { Absensi } from '../api/types'
import { JamKeluar } from '../components/JamKeluar'
import { fmtTime } from '../constants'
import { getKeluarHariOffset, parseDurasi } from '../utils/absensi'

interface EditFormValues {
  lokasi: string
  jam_masuk: Dayjs
  durasi_jam: number
  durasi_menit: number
}

export function AbsensiTab() {
  const { message } = App.useApp()
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<number>()
  const { data: absensi, isLoading } = useAbsensi({
    karyawan: karyawanId,
    bulan: month.format('YYYY-MM'),
  })
  const { data: karyawan } = useKaryawan()
  const { data: lokasi } = useLokasi()
  const { update, remove } = useAbsensiMutations()

  const [editing, setEditing] = useState<Absensi | null>(null)
  const [form] = Form.useForm<EditFormValues>()

  const jamMasuk = Form.useWatch('jam_masuk', form)
  const durasiJam = Form.useWatch('durasi_jam', form)
  const durasiMenit = Form.useWatch('durasi_menit', form)
  const computedJamKeluar = useMemo(() => {
    if (!jamMasuk) return null
    return jamMasuk.add(durasiJam ?? 0, 'hour').add(durasiMenit ?? 0, 'minute')
  }, [jamMasuk, durasiJam, durasiMenit])
  const computedKeluarHariOffset = useMemo(() => {
    if (!editing || !jamMasuk) return 0
    return getKeluarHariOffset(editing.tanggal, jamMasuk, durasiJam ?? 0, durasiMenit ?? 0)
  }, [editing, jamMasuk, durasiJam, durasiMenit])

  const openEdit = (record: Absensi) => {
    const { jam, menit } = parseDurasi(record.durasi)
    setEditing(record)
    form.setFieldsValue({
      lokasi: record.lokasi,
      jam_masuk: dayjs(record.jam_masuk, 'HH:mm:ss'),
      durasi_jam: jam,
      durasi_menit: menit,
    })
  }

  const handleSubmit = async () => {
    if (!editing) return
    const values = await form.validateFields()
    await update.mutateAsync({
      id: editing.id,
      lokasi: values.lokasi,
      jam_masuk: values.jam_masuk.format('HH:mm:00'),
      durasi: `${String(values.durasi_jam).padStart(2, '0')}:${String(values.durasi_menit).padStart(2, '0')}:00`,
    })
    message.success('Absensi diperbarui')
    setEditing(null)
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Select
          placeholder="Semua karyawan"
          style={{ minWidth: 180 }}
          allowClear
          options={(karyawan ?? []).map((k) => ({ label: k.nama, value: k.id }))}
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
      <Table<Absensi>
        rowKey="id"
        size="small"
        loading={isLoading}
        dataSource={absensi}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        columns={[
          { title: 'Tanggal', dataIndex: 'tanggal', sorter: (a, b) => a.tanggal.localeCompare(b.tanggal) },
          { title: 'Karyawan', dataIndex: 'karyawan_nama' },
          { title: 'Lokasi', dataIndex: 'lokasi_nama' },
          { title: 'Jam Masuk', dataIndex: 'jam_masuk', render: fmtTime },
          { title: 'Durasi', dataIndex: 'durasi', render: (d: string) => d.slice(0, 5) },
          {
            title: 'Jam Keluar',
            render: (_, record) => (
              <JamKeluar
                jamKeluar={record.jam_keluar}
                keluarHariOffset={record.keluar_hari_offset}
              />
            ),
          },
          {
            title: 'Aksi',
            width: 160,
            render: (_, record) => (
              <Space>
                <Button size="small" onClick={() => openEdit(record)}>
                  Edit
                </Button>
                <Popconfirm
                  title="Hapus absensi ini?"
                  onConfirm={async () => {
                    await remove.mutateAsync(record.id)
                    message.success('Absensi dihapus')
                  }}
                >
                  <Button size="small" danger>
                    Hapus
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal
        title={editing ? `Edit Absensi — ${editing.karyawan_nama}, ${editing.tanggal}` : 'Edit Absensi'}
        open={editing != null}
        onOk={handleSubmit}
        confirmLoading={update.isPending}
        onCancel={() => setEditing(null)}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="lokasi" label="Lokasi" rules={[{ required: true, message: 'Pilih lokasi' }]}>
            <Select options={(lokasi ?? []).map((l) => ({ label: l.nama, value: l.id }))} />
          </Form.Item>
          <Form.Item name="jam_masuk" label="Jam Masuk" rules={[{ required: true, message: 'Wajib diisi' }]}>
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Space>
            <Form.Item name="durasi_jam" label="Durasi (jam)" rules={[{ required: true, message: 'Wajib' }]}>
              <InputNumber min={0} max={24} />
            </Form.Item>
            <Form.Item name="durasi_menit" label="Durasi (menit)" rules={[{ required: true, message: 'Wajib' }]}>
              <InputNumber min={0} max={59} />
            </Form.Item>
          </Space>
          <Typography.Paragraph type="secondary">
            Jam keluar (dihitung otomatis):{' '}
            <Typography.Text strong>
              {computedJamKeluar ? (
                <JamKeluar
                  jamKeluar={computedJamKeluar.format('HH:mm:ss')}
                  keluarHariOffset={computedKeluarHariOffset}
                />
              ) : (
                '-'
              )}
            </Typography.Text>
          </Typography.Paragraph>
        </Form>
      </Modal>
    </Space>
  )
}

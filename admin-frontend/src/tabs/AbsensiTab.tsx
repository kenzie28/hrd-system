import { useMemo, useState } from 'react'
import {
  App,
  Button,
  DatePicker,
  Empty,
  Form,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  TimePicker,
  Typography,
} from 'antd'
import dayjs, { Dayjs } from 'dayjs'
import {
  useAbsensi,
  useAbsensiMutations,
  useKaryawan,
  useLembur,
  useLemburDayMutations,
  useLokasi,
} from '../api/hooks'
import type { Absensi } from '../api/types'
import { JamKeluar } from '../components/JamKeluar'
import { fmtTime } from '../constants'
import { durasiFromTimes } from '../utils/absensi'

interface EditFormValues {
  lokasi: string
  jam_masuk: Dayjs
  jam_keluar: Dayjs
}

interface AbsensiTabProps {
  initialKaryawanId?: string
  initialBulan?: string
}

export function AbsensiTab({ initialKaryawanId, initialBulan }: AbsensiTabProps) {
  const { message } = App.useApp()
  const [month, setMonth] = useState(() => initialBulan ? dayjs(initialBulan) : dayjs())
  const [karyawanId, setKaryawanId] = useState<string | undefined>(initialKaryawanId)
  const { data: absensi, isLoading } = useAbsensi({
    karyawan_id: karyawanId,
    bulan: month.format('YYYY-MM'),
  })
  const { data: approvedLembur, isLoading: lemburLoading } = useLembur(
    {
      karyawan_id: karyawanId,
      bulan: month.format('YYYY-MM'),
    },
    Boolean(karyawanId),
  )
  const { data: karyawan } = useKaryawan()
  const { data: lokasi } = useLokasi()
  const { update, remove } = useAbsensiMutations()
  const { add: addLembur, remove: removeLembur } = useLemburDayMutations()
  const [pendingLemburTanggal, setPendingLemburTanggal] = useState<string | null>(null)

  const [editing, setEditing] = useState<Absensi | null>(null)
  const [form] = Form.useForm<EditFormValues>()

  const karyawanOptions = useMemo(
    () => (karyawan ?? []).map((k) => ({ label: `${k.nama} (${k.karyawan_id})`, value: k.karyawan_id })),
    [karyawan],
  )
  const lemburDates = useMemo(
    () => new Set((approvedLembur ?? []).map((row) => row.tanggal)),
    [approvedLembur],
  )

  const toggleLembur = async (record: Absensi) => {
    const hasLembur = lemburDates.has(record.tanggal)
    setPendingLemburTanggal(record.tanggal)
    try {
      if (hasLembur) {
        await removeLembur.mutateAsync({
          karyawan_id: record.karyawan_id,
          tanggal: record.tanggal,
        })
        message.success('Lembur dihapus')
      } else {
        await addLembur.mutateAsync({
          karyawan_id: record.karyawan_id,
          tanggal: record.tanggal,
        })
        message.success('Lembur ditambahkan')
      }
    } catch {
      message.error(hasLembur ? 'Gagal menghapus lembur.' : 'Gagal menambahkan lembur.')
    } finally {
      setPendingLemburTanggal(null)
    }
  }

  const openEdit = (record: Absensi) => {
    setEditing(record)
    form.setFieldsValue({
      lokasi: record.lokasi,
      jam_masuk: dayjs(`2000-01-01T${record.jam_masuk}`),
      jam_keluar: dayjs(`2000-01-01T${record.jam_keluar}`),
    })
  }

  const handleSubmit = async () => {
    if (!editing) return
    const values = await form.validateFields()
    await update.mutateAsync({
      id: editing.id,
      lokasi: values.lokasi,
      jam_masuk: values.jam_masuk.format('HH:mm:00'),
      durasi: durasiFromTimes(values.jam_masuk, values.jam_keluar),
    })
    message.success('Absensi diperbarui')
    setEditing(null)
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Select
          placeholder="Pilih karyawan"
          style={{ minWidth: 280, maxWidth: '100%' }}
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

      {!karyawanId ? (
        <Empty description="Pilih karyawan untuk meninjau riwayat absensinya." />
      ) : (
        <Table<Absensi>
          rowKey="id"
          size="small"
          loading={isLoading}
          dataSource={absensi}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          scroll={{ x: 'max-content' }}
          columns={[
            {
              title: 'Tanggal',
              dataIndex: 'tanggal',
              sorter: (a, b) => a.tanggal.localeCompare(b.tanggal),
              defaultSortOrder: 'descend',
            },
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
              width: 300,
              render: (_, record) => (
                <Space wrap>
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
                  {!lemburLoading && (
                    <Button
                      size="small"
                      loading={pendingLemburTanggal === record.tanggal}
                      onClick={() => toggleLembur(record)}
                    >
                      {lemburDates.has(record.tanggal) ? 'Remove Lembur' : 'Add Lembur'}
                    </Button>
                  )}
                </Space>
              ),
            },
          ]}
        />
      )}

      <Modal
        title={
          editing
            ? `Edit Absensi — ${editing.karyawan_nama} (${editing.karyawan_id}), ${editing.tanggal}`
            : 'Edit Absensi'
        }
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
          <Form.Item name="jam_keluar" label="Jam Keluar" rules={[{ required: true, message: 'Wajib diisi' }]}>
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Typography.Text type="secondary">
            Jam keluar yang sama atau lebih awal dari jam masuk dianggap hari berikutnya.
          </Typography.Text>
        </Form>
      </Modal>
    </Space>
  )
}

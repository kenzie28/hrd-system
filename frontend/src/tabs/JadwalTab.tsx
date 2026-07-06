import { useMemo, useState } from 'react'
import {
  App,
  Button,
  DatePicker,
  Form,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tag,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { useJadwal, useJadwalMutations, useKaryawan, useShifts } from '../api/hooks'
import type { Jadwal } from '../api/types'
import { ViewModeToggle } from '../components/ViewModeToggle'
import { fmtTime } from '../constants'

interface BulkFormValues {
  karyawan_ids: number[]
  shift_id: number
  range: [Dayjs, Dayjs]
}

export function JadwalTab() {
  const { message } = App.useApp()
  const [month, setMonth] = useState(() => dayjs())
  const [karyawanId, setKaryawanId] = useState<number>()
  const filters = { karyawan: karyawanId, bulan: month.format('YYYY-MM') }

  const { data: jadwal, isLoading } = useJadwal(filters)
  const { data: karyawan } = useKaryawan()
  const { data: shifts } = useShifts()
  const { bulkCreate, update, remove } = useJadwalMutations()

  const [bulkOpen, setBulkOpen] = useState(false)
  const [editing, setEditing] = useState<Jadwal | null>(null)
  const [bulkForm] = Form.useForm<BulkFormValues>()
  const [editForm] = Form.useForm<{ shift: number }>()

  const shiftOptions = useMemo(
    () =>
      (shifts ?? []).map((s) => ({
        label: `${fmtTime(s.jam_masuk)} - ${fmtTime(s.jam_keluar)}`,
        value: s.id,
      })),
    [shifts],
  )
  const karyawanOptions = useMemo(
    () => (karyawan ?? []).map((k) => ({ label: k.nama, value: k.id })),
    [karyawan],
  )

  const handleBulkSubmit = async () => {
    const values = await bulkForm.validateFields()
    const res = await bulkCreate.mutateAsync({
      karyawan_ids: values.karyawan_ids,
      shift_id: values.shift_id,
      tanggal_mulai: values.range[0].format('YYYY-MM-DD'),
      tanggal_selesai: values.range[1].format('YYYY-MM-DD'),
    })
    message.success(
      `${res.data.created} jadwal dibuat` +
        (res.data.skipped_existing ? `, ${res.data.skipped_existing} sudah ada (dilewati)` : ''),
    )
    setBulkOpen(false)
    bulkForm.resetFields()
  }

  const handleEditSubmit = async () => {
    if (!editing) return
    const values = await editForm.validateFields()
    await update.mutateAsync({ id: editing.id, shift: values.shift })
    message.success('Jadwal diperbarui')
    setEditing(null)
  }

  const shiftLabel = (j: Jadwal) =>
    `${fmtTime(j.shift_detail.jam_masuk)} - ${fmtTime(j.shift_detail.jam_keluar)}`

  const actions = (j: Jadwal) => (
    <Space>
      <Button
        size="small"
        onClick={() => {
          setEditing(j)
          editForm.setFieldsValue({ shift: j.shift })
        }}
      >
        Edit
      </Button>
      <Popconfirm
        title="Hapus jadwal ini?"
        onConfirm={async () => {
          await remove.mutateAsync(j.id)
          message.success('Jadwal dihapus')
        }}
      >
        <Button size="small" danger>
          Hapus
        </Button>
      </Popconfirm>
    </Space>
  )

  return (
    <>
      <ViewModeToggle<Jadwal>
        data={jadwal ?? []}
        loading={isLoading}
        karyawanId={karyawanId}
        onKaryawanChange={setKaryawanId}
        month={month}
        onMonthChange={setMonth}
        getDate={(j) => j.tanggal}
        toolbarExtra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setBulkOpen(true)}>
            Buat Jadwal (Bulk)
          </Button>
        }
        columns={[
          { title: 'Tanggal', dataIndex: 'tanggal', sorter: (a, b) => a.tanggal.localeCompare(b.tanggal) },
          { title: 'Karyawan', dataIndex: 'karyawan_nama' },
          { title: 'Shift', render: (_, j) => <Tag color="blue">{shiftLabel(j)}</Tag> },
          { title: 'Aksi', width: 160, render: (_, j) => actions(j) },
        ]}
        renderBadge={(j) => (
          <Tag color="blue" style={{ fontSize: 11, lineHeight: '16px', margin: 0 }}>
            {j.karyawan_nama.split(' ')[0]} {shiftLabel(j)}
          </Tag>
        )}
      />

      <Modal
        title="Buat Jadwal (Bulk)"
        open={bulkOpen}
        onOk={handleBulkSubmit}
        confirmLoading={bulkCreate.isPending}
        onCancel={() => setBulkOpen(false)}
        destroyOnHidden
      >
        <Form form={bulkForm} layout="vertical">
          <Form.Item
            name="karyawan_ids"
            label="Karyawan"
            rules={[{ required: true, message: 'Pilih minimal satu karyawan' }]}
          >
            <Select
              mode="multiple"
              options={karyawanOptions}
              placeholder="Pilih karyawan"
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="shift_id" label="Shift" rules={[{ required: true, message: 'Pilih shift' }]}>
            <Select options={shiftOptions} placeholder="Pilih shift" />
          </Form.Item>
          <Form.Item name="range" label="Rentang Tanggal" rules={[{ required: true, message: 'Pilih rentang tanggal' }]}>
            <DatePicker.RangePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editing ? `Edit Jadwal — ${editing.karyawan_nama}, ${editing.tanggal}` : 'Edit Jadwal'}
        open={editing != null}
        onOk={handleEditSubmit}
        confirmLoading={update.isPending}
        onCancel={() => setEditing(null)}
        destroyOnHidden
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="shift" label="Shift" rules={[{ required: true, message: 'Pilih shift' }]}>
            <Select options={shiftOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

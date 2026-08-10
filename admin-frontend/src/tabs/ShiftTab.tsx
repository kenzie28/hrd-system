import { useMemo, useState } from 'react'
import { App, Button, Empty, Form, Modal, Popconfirm, Select, Space, Table } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { useLokasi, useShiftMutations, useShifts } from '../api/hooks'
import type { HariKerja, Shift } from '../api/types'
import { TimeInput } from '../components/TimeInput'
import { HARI_KERJA_OPTIONS, HARI_KERJA_ORDER, fmtTime } from '../constants'

interface ShiftFormValues {
  hari: HariKerja
  jam_masuk: Dayjs
  jam_keluar: Dayjs
}

export function ShiftTab() {
  const { message } = App.useApp()
  const { data: lokasi } = useLokasi()
  const [lokasiKerja, setLokasiKerja] = useState<string>()
  const { data: shifts, isLoading } = useShifts(lokasiKerja)
  const { create, update, remove } = useShiftMutations()

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Shift | null>(null)
  const [form] = Form.useForm<ShiftFormValues>()

  const lokasiOptions = useMemo(
    () => (lokasi ?? []).map((l) => ({ label: l.nama, value: l.id })),
    [lokasi],
  )

  const sortedShifts = useMemo(
    () =>
      [...(shifts ?? [])].sort(
        (a, b) =>
          HARI_KERJA_ORDER[a.hari] - HARI_KERJA_ORDER[b.hari] ||
          a.jam_masuk.localeCompare(b.jam_masuk),
      ),
    [shifts],
  )

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (shift: Shift) => {
    setEditing(shift)
    form.setFieldsValue({
      hari: shift.hari,
      jam_masuk: dayjs(shift.jam_masuk, 'HH:mm:ss'),
      jam_keluar: dayjs(shift.jam_keluar, 'HH:mm:ss'),
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    if (!lokasiKerja) return
    const values = await form.validateFields()
    const payload = {
      lokasi_kerja: lokasiKerja,
      hari: values.hari,
      jam_masuk: values.jam_masuk.format('HH:mm:00'),
      jam_keluar: values.jam_keluar.format('HH:mm:00'),
    }
    if (editing) {
      await update.mutateAsync({ id: editing.id, ...payload })
      message.success('Shift diperbarui')
    } else {
      await create.mutateAsync(payload)
      message.success('Shift dibuat')
    }
    setModalOpen(false)
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Select
          placeholder="Pilih lokasi kerja"
          style={{ minWidth: 240 }}
          options={lokasiOptions}
          value={lokasiKerja}
          onChange={setLokasiKerja}
          showSearch
          optionFilterProp="label"
        />
        <Button
          type="primary"
          icon={<PlusOutlined />}
          disabled={!lokasiKerja}
          onClick={openCreate}
        >
          Tambah Shift
        </Button>
      </Space>

      {!lokasiKerja ? (
        <Empty description="Pilih lokasi kerja untuk mengelola shift." />
      ) : (
        <Table<Shift>
          rowKey="id"
          size="small"
          loading={isLoading}
          dataSource={sortedShifts}
          pagination={false}
          columns={[
            { title: 'Hari', dataIndex: 'hari_display', width: 100 },
            { title: 'Jam Masuk', dataIndex: 'jam_masuk', render: fmtTime },
            { title: 'Jam Keluar', dataIndex: 'jam_keluar', render: fmtTime },
            {
              title: 'Aksi',
              width: 160,
              render: (_, shift) => (
                <Space>
                  <Button size="small" onClick={() => openEdit(shift)}>
                    Edit
                  </Button>
                  <Popconfirm
                    title="Hapus shift ini?"
                    onConfirm={async () => {
                      await remove.mutateAsync(shift.id)
                      message.success('Shift dihapus')
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
      )}

      <Modal
        title={editing ? 'Edit Shift' : 'Tambah Shift'}
        open={modalOpen}
        onOk={handleSubmit}
        confirmLoading={create.isPending || update.isPending}
        onCancel={() => setModalOpen(false)}
        destroyOnHidden
        width={420}
        okText={editing ? 'Simpan' : 'Tambah'}
        cancelText="Batal"
      >
        <Form form={form} layout="vertical" requiredMark="optional">
          <Form.Item
            name="hari"
            label="Hari"
            rules={[{ required: true, message: 'Wajib diisi' }]}
          >
            <Select options={HARI_KERJA_OPTIONS} placeholder="Pilih hari" />
          </Form.Item>
          <Form.Item
            name="jam_masuk"
            label="Jam Masuk"
            rules={[{ required: true, message: 'Wajib diisi' }]}
          >
            <TimeInput classNames={{ popup: { root: 'shift-time-panel' } }} />
          </Form.Item>
          <Form.Item
            name="jam_keluar"
            label="Jam Keluar"
            rules={[{ required: true, message: 'Wajib diisi' }]}
          >
            <TimeInput classNames={{ popup: { root: 'shift-time-panel' } }} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}

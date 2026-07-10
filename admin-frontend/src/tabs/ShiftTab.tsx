import { useState } from 'react'
import { App, Button, Form, Modal, Popconfirm, Space, Table } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { useShiftMutations, useShifts } from '../api/hooks'
import type { Shift } from '../api/types'
import { TimeInput } from '../components/TimeInput'
import { fmtTime } from '../constants'

interface ShiftFormValues {
  jam_masuk: Dayjs
  jam_keluar: Dayjs
}

export function ShiftTab() {
  const { message } = App.useApp()
  const { data: shifts, isLoading } = useShifts()
  const { create, update, remove } = useShiftMutations()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Shift | null>(null)
  const [form] = Form.useForm<ShiftFormValues>()

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (shift: Shift) => {
    setEditing(shift)
    form.setFieldsValue({
      jam_masuk: dayjs(shift.jam_masuk, 'HH:mm:ss'),
      jam_keluar: dayjs(shift.jam_keluar, 'HH:mm:ss'),
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
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
      <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
        Tambah Shift
      </Button>
      <Table<Shift>
        rowKey="id"
        size="small"
        loading={isLoading}
        dataSource={shifts}
        pagination={false}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          {
            title: 'Jam Masuk',
            dataIndex: 'jam_masuk',
            render: fmtTime,
          },
          {
            title: 'Jam Keluar',
            dataIndex: 'jam_keluar',
            render: fmtTime,
          },
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

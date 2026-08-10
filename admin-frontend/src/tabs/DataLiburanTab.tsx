import { useState } from 'react'
import { PlusOutlined } from '@ant-design/icons'
import {
  App,
  Button,
  DatePicker,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Tag,
} from 'antd'
import dayjs, { Dayjs } from 'dayjs'
import { useLiburan, useLiburanMutations } from '../api/hooks'
import type { Liburan } from '../api/types'
import { ViewModeToggle } from '../components/ViewModeToggle'

interface LiburanFormValues {
  nama: string
  tanggal: Dayjs
}

export function DataLiburanTab() {
  const { message } = App.useApp()
  const [month, setMonth] = useState(() => dayjs())
  const filters = { bulan: month.format('YYYY-MM') }

  const { data: liburan, isLoading } = useLiburan(filters)
  const { create, update, remove } = useLiburanMutations()

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Liburan | null>(null)
  const [form] = Form.useForm<LiburanFormValues>()

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ tanggal: month.startOf('month') })
    setModalOpen(true)
  }

  const openEdit = (row: Liburan) => {
    setEditing(row)
    form.setFieldsValue({
      nama: row.nama,
      tanggal: dayjs(row.tanggal),
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      nama: values.nama.trim(),
      tanggal: values.tanggal.format('YYYY-MM-DD'),
    }
    if (editing) {
      await update.mutateAsync({ id: editing.id, ...payload })
      message.success('Liburan diperbarui')
    } else {
      await create.mutateAsync(payload)
      message.success('Liburan ditambahkan')
    }
    setModalOpen(false)
  }

  return (
    <>
      <ViewModeToggle<Liburan>
        data={liburan ?? []}
        loading={isLoading}
        hideKaryawanFilter
        month={month}
        onMonthChange={setMonth}
        getDate={(row) => row.tanggal}
        renderBadge={(row) => <Tag>{row.nama}</Tag>}
        toolbarExtra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Tambah Liburan
          </Button>
        }
        columns={[
          {
            title: 'Tanggal',
            dataIndex: 'tanggal',
            width: 130,
            render: (v: string) => dayjs(v).format('DD MMM YYYY'),
          },
          { title: 'Nama', dataIndex: 'nama' },
          {
            title: 'Aksi',
            width: 160,
            render: (_, row) => (
              <Space wrap>
                <Button size="small" onClick={() => openEdit(row)}>
                  Edit
                </Button>
                <Popconfirm
                  title="Hapus liburan ini?"
                  onConfirm={async () => {
                    await remove.mutateAsync(row.id)
                    message.success('Liburan dihapus')
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
        title={editing ? 'Edit Liburan' : 'Tambah Liburan'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={create.isPending || update.isPending}
        destroyOnHidden
        okText="Simpan"
        cancelText="Batal"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="nama"
            label="Nama"
            rules={[{ required: true, message: 'Nama wajib diisi' }]}
          >
            <Input placeholder="Contoh: Hari Raya Idul Fitri" maxLength={64} />
          </Form.Item>
          <Form.Item
            name="tanggal"
            label="Tanggal"
            rules={[{ required: true, message: 'Tanggal wajib diisi' }]}
          >
            <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

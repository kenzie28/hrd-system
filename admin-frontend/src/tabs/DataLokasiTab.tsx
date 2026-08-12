import { useMemo, useState } from 'react'
import { EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import {
  App,
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import axios from 'axios'
import {
  useLokasi,
  useLokasiCreate,
  useLokasiDelete,
  useLokasiUpdate,
} from '../api/hooks'
import type { Lokasi } from '../api/types'

interface LokasiFormValues {
  id: string
  nama: string
}

export function DataLokasiTab() {
  const { message } = App.useApp()
  const { data: lokasi, isLoading } = useLokasi()
  const create = useLokasiCreate()
  const update = useLokasiUpdate()
  const remove = useLokasiDelete()

  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingLabel, setEditingLabel] = useState('')
  const [form] = Form.useForm<LokasiFormValues>()

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return lokasi ?? []
    return (lokasi ?? []).filter(
      (l) =>
        l.id.toLowerCase().includes(q) || l.nama.toLowerCase().includes(q),
    )
  }, [lokasi, search])

  const isEditing = editingId !== null

  const openCreate = () => {
    setEditingId(null)
    setEditingLabel('')
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (record: Lokasi) => {
    setEditingId(record.id)
    setEditingLabel(`${record.id} — ${record.nama}`)
    form.setFieldsValue({
      id: record.id,
      nama: record.nama,
    })
    setModalOpen(true)
  }

  const apiErrorDetail = (err: unknown, fallback: string) => {
    if (axios.isAxiosError(err)) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string' && detail.trim()) return detail
    }
    return fallback
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      id: values.id.trim(),
      nama: values.nama.trim(),
    }
    try {
      if (isEditing) {
        await update.mutateAsync({ id: editingId, nama: payload.nama })
        message.success('Lokasi diperbarui')
      } else {
        await create.mutateAsync(payload)
        message.success('Lokasi ditambahkan')
      }
      setModalOpen(false)
    } catch (err) {
      message.error(
        apiErrorDetail(
          err,
          isEditing ? 'Gagal memperbarui lokasi' : 'Gagal menambahkan lokasi',
        ),
      )
    }
  }

  const handleDelete = async () => {
    if (editingId == null) return
    try {
      await remove.mutateAsync(editingId)
      message.success('Lokasi dihapus')
      setModalOpen(false)
    } catch (err) {
      message.error(apiErrorDetail(err, 'Gagal menghapus lokasi'))
    }
  }

  const columns: ColumnsType<Lokasi> = [
    {
      key: 'id',
      title: 'ID',
      dataIndex: 'id',
      width: 80,
    },
    {
      key: 'nama',
      title: 'Nama',
      dataIndex: 'nama',
    },
    {
      key: 'aksi',
      title: 'Aksi',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Button
          size="small"
          icon={<EditOutlined />}
          onClick={() => openEdit(record)}
        >
          Edit
        </Button>
      ),
    },
  ]

  return (
    <>
      <Space
        wrap
        style={{ width: '100%', marginBottom: 16, justifyContent: 'space-between' }}
      >
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Cari ID / nama"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: '100%', maxWidth: 280 }}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Tambah Lokasi
        </Button>
      </Space>

      <Table<Lokasi>
        rowKey="id"
        size="small"
        loading={isLoading}
        dataSource={filtered}
        columns={columns}
        scroll={{ x: true }}
        pagination={{ pageSize: 20, showSizeChanger: false }}
      />

      <Modal
        title={isEditing ? 'Edit Lokasi' : 'Tambah Lokasi'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        destroyOnHidden
        width={480}
        footer={
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <div>
              {isEditing ? (
                <Popconfirm
                  title="Hapus lokasi ini?"
                  description={
                    editingLabel
                      ? `${editingLabel} akan dihapus. Tindakan ini tidak bisa dibatalkan.`
                      : 'Tindakan ini tidak bisa dibatalkan.'
                  }
                  okText="Hapus"
                  cancelText="Batal"
                  okButtonProps={{ danger: true, loading: remove.isPending }}
                  onConfirm={handleDelete}
                >
                  <Button danger loading={remove.isPending}>
                    Hapus
                  </Button>
                </Popconfirm>
              ) : null}
            </div>
            <Space>
              <Button onClick={() => setModalOpen(false)}>Batal</Button>
              <Button
                type="primary"
                loading={create.isPending || update.isPending}
                onClick={handleSubmit}
              >
                Simpan
              </Button>
            </Space>
          </div>
        }
      >
        <Form form={form} layout="vertical" requiredMark="optional">
          <Form.Item
            name="id"
            label="ID Lokasi"
            rules={[
              { required: true, message: 'ID lokasi wajib diisi' },
              { max: 2, message: 'Maksimal 2 karakter' },
            ]}
          >
            <Input placeholder="Contoh: 23" maxLength={2} disabled={isEditing} />
          </Form.Item>
          <Form.Item
            name="nama"
            label="Nama"
            rules={[
              { required: true, message: 'Nama wajib diisi' },
              { max: 128, message: 'Maksimal 128 karakter' },
            ]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

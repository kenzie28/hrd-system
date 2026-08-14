import { useMemo, useState } from 'react'
import {
  EditOutlined,
  FilterOutlined,
  PlusOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import {
  App,
  Button,
  Checkbox,
  Dropdown,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import axios from 'axios'
import {
  useKaryawan,
  useKaryawanCreate,
  useKaryawanDelete,
  useKaryawanUpdate,
  useLokasi,
} from '../api/hooks'
import type { Karyawan } from '../api/types'

type ColumnKey =
  | 'karyawan_id'
  | 'nama'
  | 'lokasi_kerja'
  | 'jabatan'
  | 'wilayah'
  | 'level'
  | 'cuti_tahunan'

const ALL_COLUMN_KEYS: ColumnKey[] = [
  'karyawan_id',
  'nama',
  'lokasi_kerja',
  'jabatan',
  'wilayah',
  'level',
  'cuti_tahunan',
]

const COLUMN_LABELS: Record<ColumnKey, string> = {
  karyawan_id: 'ID Karyawan',
  nama: 'Nama',
  lokasi_kerja: 'Lokasi Kerja',
  jabatan: 'Jabatan',
  wilayah: 'Wilayah',
  level: 'Level',
  cuti_tahunan: 'Cuti',
}

const STORAGE_KEY = 'master-karyawan-columns'

const LEVEL_OPTIONS = Array.from({ length: 8 }, (_, i) => ({
  value: i + 1,
  label: String(i + 1),
}))

function loadVisibleColumns(): ColumnKey[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return [...ALL_COLUMN_KEYS]
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...ALL_COLUMN_KEYS]
    const valid = parsed.filter((k): k is ColumnKey =>
      ALL_COLUMN_KEYS.includes(k as ColumnKey),
    )
    return valid.length > 0 ? valid : [...ALL_COLUMN_KEYS]
  } catch {
    return [...ALL_COLUMN_KEYS]
  }
}

interface KaryawanFormValues {
  karyawan_id: string
  nama: string
  level: number
  jabatan?: string
  wilayah?: string
  lokasi_kerja?: string | null
  cuti_tahunan: number
}

export function DataKaryawanTab() {
  const { message } = App.useApp()
  const { data: karyawan, isLoading } = useKaryawan()
  const { data: lokasiList } = useLokasi()
  const create = useKaryawanCreate()
  const update = useKaryawanUpdate()
  const remove = useKaryawanDelete()

  const [search, setSearch] = useState('')
  const [visibleColumns, setVisibleColumns] = useState<ColumnKey[]>(loadVisibleColumns)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingLabel, setEditingLabel] = useState('')
  const [form] = Form.useForm<KaryawanFormValues>()

  const lokasiMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const loc of lokasiList ?? []) {
      map.set(loc.id, loc.nama)
    }
    return map
  }, [lokasiList])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return karyawan ?? []
    return (karyawan ?? []).filter(
      (k) =>
        k.nama.toLowerCase().includes(q) ||
        k.karyawan_id.toLowerCase().includes(q) ||
        (k.jabatan ?? '').toLowerCase().includes(q),
    )
  }, [karyawan, search])

  const setColumns = (keys: ColumnKey[]) => {
    const next = keys.length > 0 ? keys : [...ALL_COLUMN_KEYS]
    setVisibleColumns(next)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }

  const allColumns: ColumnsType<Karyawan> = [
    {
      key: 'karyawan_id',
      title: COLUMN_LABELS.karyawan_id,
      dataIndex: 'karyawan_id',
      width: 120,
    },
    {
      key: 'nama',
      title: COLUMN_LABELS.nama,
      dataIndex: 'nama',
      width: 180,
    },
    {
      key: 'lokasi_kerja',
      title: COLUMN_LABELS.lokasi_kerja,
      dataIndex: 'lokasi_kerja',
      width: 160,
      render: (id: string | null) =>
        id ? (lokasiMap.get(id) ?? id) : '—',
    },
    {
      key: 'jabatan',
      title: COLUMN_LABELS.jabatan,
      dataIndex: 'jabatan',
      width: 160,
      render: (v: string) => v || '—',
    },
    {
      key: 'wilayah',
      title: COLUMN_LABELS.wilayah,
      dataIndex: 'wilayah',
      width: 100,
      render: (v: string) => v || '—',
    },
    {
      key: 'level',
      title: COLUMN_LABELS.level,
      dataIndex: 'level',
      width: 80,
    },
    {
      key: 'cuti_tahunan',
      title: COLUMN_LABELS.cuti_tahunan,
      dataIndex: 'cuti_tahunan',
      width: 100,
    },
  ]

  const columns: ColumnsType<Karyawan> = [
    ...allColumns.filter((col) => visibleColumns.includes(col.key as ColumnKey)),
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

  const isEditing = editingId !== null

  const openCreate = () => {
    setEditingId(null)
    setEditingLabel('')
    form.resetFields()
    form.setFieldsValue({
      level: 1,
      jabatan: '',
      wilayah: '',
      lokasi_kerja: null,
      cuti_tahunan: 12,
    })
    setModalOpen(true)
  }

  const openEdit = (record: Karyawan) => {
    setEditingId(record.karyawan_id)
    setEditingLabel(`${record.karyawan_id} — ${record.nama}`)
    form.setFieldsValue({
      karyawan_id: record.karyawan_id,
      nama: record.nama,
      level: record.level,
      jabatan: record.jabatan,
      wilayah: record.wilayah,
      lokasi_kerja: record.lokasi_kerja,
      cuti_tahunan: record.cuti_tahunan,
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
      karyawan_id: values.karyawan_id.trim(),
      nama: values.nama.trim(),
      level: values.level,
      jabatan: (values.jabatan ?? '').trim(),
      wilayah: (values.wilayah ?? '').trim(),
      lokasi_kerja: values.lokasi_kerja || null,
      cuti_tahunan: values.cuti_tahunan,
    }
    try {
      if (isEditing) {
        await update.mutateAsync({ karyawan_id: editingId, ...payload })
        message.success('Karyawan diperbarui')
      } else {
        await create.mutateAsync(payload)
        message.success('Karyawan ditambahkan')
      }
      setModalOpen(false)
    } catch (err) {
      message.error(
        apiErrorDetail(
          err,
          isEditing ? 'Gagal memperbarui karyawan' : 'Gagal menambahkan karyawan',
        ),
      )
    }
  }

  const handleDelete = async () => {
    if (editingId == null) return
    try {
      await remove.mutateAsync(editingId)
      message.success('Karyawan dihapus')
      setModalOpen(false)
    } catch (err) {
      message.error(apiErrorDetail(err, 'Gagal menghapus karyawan'))
    }
  }

  return (
    <>
      <Space
        wrap
        style={{ width: '100%', marginBottom: 16, justifyContent: 'space-between' }}
      >
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Cari nama / ID / jabatan"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: '100%', maxWidth: 280 }}
        />
        <Space wrap>
          <Dropdown
            trigger={['click']}
            dropdownRender={() => (
              <div
                style={{
                  padding: 12,
                  background: '#fff',
                  borderRadius: 8,
                  boxShadow: '0 6px 16px rgba(0,0,0,0.08)',
                  minWidth: 180,
                }}
              >
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  Tampilkan kolom
                </Typography.Text>
                <Checkbox.Group
                  style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}
                  value={visibleColumns}
                  onChange={(vals) => setColumns(vals as ColumnKey[])}
                  options={ALL_COLUMN_KEYS.map((key) => ({
                    label: COLUMN_LABELS[key],
                    value: key,
                  }))}
                />
              </div>
            )}
          >
            <Button icon={<FilterOutlined />}>Kolom</Button>
          </Dropdown>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Tambah Karyawan
          </Button>
        </Space>
      </Space>

      <Table<Karyawan>
        rowKey="karyawan_id"
        size="small"
        loading={isLoading}
        dataSource={filtered}
        columns={columns}
        scroll={{ x: true }}
        pagination={{ pageSize: 20, showSizeChanger: false }}
      />

      <Modal
        title={isEditing ? 'Edit Karyawan' : 'Tambah Karyawan'}
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
                  title="Hapus karyawan ini?"
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
            name="karyawan_id"
            label="ID Karyawan"
            rules={[
              { required: true, message: 'ID karyawan wajib diisi' },
              { max: 7, message: 'Maksimal 7 karakter' },
            ]}
          >
            <Input placeholder="Contoh: 0000001" maxLength={7} disabled={isEditing} />
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
          <Form.Item
            name="level"
            label="Level"
            rules={[{ required: true, message: 'Level wajib dipilih' }]}
          >
            <Select options={LEVEL_OPTIONS} />
          </Form.Item>
          <Form.Item name="jabatan" label="Jabatan" rules={[{ max: 128 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="wilayah" label="Wilayah" rules={[{ max: 3 }]}>
            <Input maxLength={3} placeholder="Max 3 karakter" />
          </Form.Item>
          <Form.Item
            name="cuti_tahunan"
            label="Jatah Cuti Tahunan (hari)"
            rules={[{ required: true, message: 'Jatah cuti tahunan wajib diisi' }]}
          >
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="lokasi_kerja" label="Lokasi Kerja">
            <Select
              allowClear
              placeholder="Pilih lokasi"
              options={(lokasiList ?? []).map((l) => ({
                value: l.id,
                label: `${l.id} — ${l.nama}`,
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

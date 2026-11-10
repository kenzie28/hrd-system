import { useMemo, useState, type Dispatch, type SetStateAction } from 'react'
import {
  EditOutlined,
  FilterOutlined,
  PlusOutlined,
  SearchOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import {
  App,
  Badge,
  Button,
  Checkbox,
  Dropdown,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Popover,
  Select,
  Space,
  Table,
  Tag,
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
import { formatCurrency } from '../constants'

type ColumnKey =
  | 'karyawan_id'
  | 'nama'
  | 'lokasi_kerja'
  | 'jabatan'
  | 'wilayah'
  | 'level'
  | 'cuti_tahunan'
  | 'base_gaji'

const ALL_COLUMN_KEYS: ColumnKey[] = [
  'karyawan_id',
  'nama',
  'lokasi_kerja',
  'jabatan',
  'wilayah',
  'level',
  'cuti_tahunan',
  'base_gaji',
]

const COLUMN_LABELS: Record<ColumnKey, string> = {
  karyawan_id: 'ID Karyawan',
  nama: 'Nama',
  lokasi_kerja: 'Lokasi Kerja',
  jabatan: 'Jabatan',
  wilayah: 'Wilayah',
  level: 'Level',
  cuti_tahunan: 'Cuti',
  base_gaji: 'Base Gaji',
}

const STORAGE_KEY = 'master-karyawan-columns'

const LEVEL_OPTIONS = Array.from({ length: 8 }, (_, i) => ({
  value: i + 1,
  label: String(i + 1),
}))

const NO_LOKASI = '__none__'

interface KaryawanFilters {
  karyawan_id: string
  nama: string
  lokasi: string[]
  jabatan: string
  wilayah: string
  level: number[]
  cutiMin: number | null
  cutiMax: number | null
  gajiMin: number | null
  gajiMax: number | null
}

function emptyFilters(): KaryawanFilters {
  return {
    karyawan_id: '',
    nama: '',
    lokasi: [],
    jabatan: '',
    wilayah: '',
    level: [],
    cutiMin: null,
    cutiMax: null,
    gajiMin: null,
    gajiMax: null,
  }
}

function includesText(value: string, query: string) {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return value.toLowerCase().includes(q)
}

function inRange(value: number, min: number | null, max: number | null) {
  if (min != null && value < min) return false
  if (max != null && value > max) return false
  return true
}

function rangeInvalid(min: number | null, max: number | null) {
  return min != null && max != null && min > max
}

function rangeLabel(
  min: number | null,
  max: number | null,
  format: (value: number) => string = String,
) {
  if (min != null && max != null) return `${format(min)} – ${format(max)}`
  if (min != null) return `≥ ${format(min)}`
  if (max != null) return `≤ ${format(max)}`
  return ''
}

function countActiveFilters(filters: KaryawanFilters) {
  let count = 0
  if (filters.karyawan_id.trim()) count += 1
  if (filters.nama.trim()) count += 1
  if (filters.lokasi.length > 0) count += 1
  if (filters.jabatan.trim()) count += 1
  if (filters.wilayah.trim()) count += 1
  if (filters.level.length > 0) count += 1
  if (filters.cutiMin != null || filters.cutiMax != null) count += 1
  if (filters.gajiMin != null || filters.gajiMax != null) count += 1
  return count
}

function LokasiFilter({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[]
  value: string[]
  onChange: (value: string[]) => void
}) {
  const [query, setQuery] = useState('')
  const q = query.trim().toLowerCase()
  const visible = q
    ? options.filter((opt) => opt.label.toLowerCase().includes(q))
    : options

  return (
    <div>
      <Typography.Text style={{ fontSize: 12 }}>{COLUMN_LABELS.lokasi_kerja}</Typography.Text>
      {options.length > 6 ? (
        <Input
          size="small"
          allowClear
          placeholder="Cari lokasi"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginTop: 4 }}
        />
      ) : null}
      <div style={{ maxHeight: 140, overflow: 'auto', marginTop: 6 }}>
        {visible.length === 0 ? (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            Tidak ada lokasi
          </Typography.Text>
        ) : (
          <Checkbox.Group
            style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
            value={value}
            options={visible}
            onChange={(vals) => {
              const visibleValues = new Set(visible.map((opt) => opt.value))
              const kept = value.filter((id) => !visibleValues.has(id))
              onChange([...kept, ...(vals as string[])])
            }}
          />
        )}
      </div>
    </div>
  )
}

function FilterFields({
  filters,
  setFilters,
  lokasiOptions,
}: {
  filters: KaryawanFilters
  setFilters: Dispatch<SetStateAction<KaryawanFilters>>
  lokasiOptions: { value: string; label: string }[]
}) {
  const patch = (partial: Partial<KaryawanFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }))
  }
  const active = countActiveFilters(filters)

  return (
    <div style={{ width: 280, maxHeight: 'min(70vh, 520px)', overflowY: 'auto' }}>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        Saring data
      </Typography.Text>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
        <div>
          <Typography.Text style={{ fontSize: 12 }}>{COLUMN_LABELS.karyawan_id}</Typography.Text>
          <Input
            size="small"
            allowClear
            placeholder="Mengandung"
            value={filters.karyawan_id}
            onChange={(e) => patch({ karyawan_id: e.target.value })}
            style={{ marginTop: 4 }}
          />
        </div>
        <div>
          <Typography.Text style={{ fontSize: 12 }}>{COLUMN_LABELS.nama}</Typography.Text>
          <Input
            size="small"
            allowClear
            placeholder="Mengandung"
            value={filters.nama}
            onChange={(e) => patch({ nama: e.target.value })}
            style={{ marginTop: 4 }}
          />
        </div>
        <LokasiFilter
          options={lokasiOptions}
          value={filters.lokasi}
          onChange={(lokasi) => patch({ lokasi })}
        />
        <div>
          <Typography.Text style={{ fontSize: 12 }}>{COLUMN_LABELS.jabatan}</Typography.Text>
          <Input
            size="small"
            allowClear
            placeholder="Mengandung"
            value={filters.jabatan}
            onChange={(e) => patch({ jabatan: e.target.value })}
            style={{ marginTop: 4 }}
          />
        </div>
        <div>
          <Typography.Text style={{ fontSize: 12 }}>{COLUMN_LABELS.wilayah}</Typography.Text>
          <Input
            size="small"
            allowClear
            placeholder="Mengandung"
            value={filters.wilayah}
            onChange={(e) => patch({ wilayah: e.target.value })}
            style={{ marginTop: 4 }}
          />
        </div>
        <div>
          <Typography.Text style={{ fontSize: 12 }}>{COLUMN_LABELS.level}</Typography.Text>
          <Checkbox.Group
            style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 12px', marginTop: 4 }}
            value={filters.level}
            options={LEVEL_OPTIONS}
            onChange={(vals) => patch({ level: vals as number[] })}
          />
        </div>
        <div>
          <Typography.Text style={{ fontSize: 12 }}>{COLUMN_LABELS.cuti_tahunan}</Typography.Text>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <InputNumber
              size="small"
              min={0}
              placeholder="Min"
              value={filters.cutiMin}
              onChange={(value) => patch({ cutiMin: value })}
              style={{ flex: 1, width: '100%' }}
            />
            <InputNumber
              size="small"
              min={0}
              placeholder="Maks"
              value={filters.cutiMax}
              onChange={(value) => patch({ cutiMax: value })}
              style={{ flex: 1, width: '100%' }}
            />
          </div>
          {rangeInvalid(filters.cutiMin, filters.cutiMax) ? (
            <Typography.Text type="danger" style={{ fontSize: 12 }}>
              Minimum melebihi maksimum.
            </Typography.Text>
          ) : null}
        </div>
        <div>
          <Typography.Text style={{ fontSize: 12 }}>{COLUMN_LABELS.base_gaji}</Typography.Text>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <InputNumber
              size="small"
              min={0}
              placeholder="Min"
              value={filters.gajiMin}
              onChange={(value) => patch({ gajiMin: value })}
              style={{ flex: 1, width: '100%' }}
            />
            <InputNumber
              size="small"
              min={0}
              placeholder="Maks"
              value={filters.gajiMax}
              onChange={(value) => patch({ gajiMax: value })}
              style={{ flex: 1, width: '100%' }}
            />
          </div>
          {rangeInvalid(filters.gajiMin, filters.gajiMax) ? (
            <Typography.Text type="danger" style={{ fontSize: 12 }}>
              Minimum melebihi maksimum.
            </Typography.Text>
          ) : null}
        </div>
        <Button size="small" disabled={active === 0} onClick={() => setFilters(emptyFilters())}>
          Reset
        </Button>
      </div>
    </div>
  )
}

function loadVisibleColumns(): ColumnKey[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return [...ALL_COLUMN_KEYS]
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...ALL_COLUMN_KEYS]
    const valid = parsed.filter((k): k is ColumnKey =>
      ALL_COLUMN_KEYS.includes(k as ColumnKey),
    )
    if (valid.length === 0) return [...ALL_COLUMN_KEYS]
    if (!valid.includes('base_gaji')) {
      const previous = ALL_COLUMN_KEYS.filter((k) => k !== 'base_gaji')
      if (previous.every((k) => valid.includes(k))) valid.push('base_gaji')
    }
    return valid
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
  const [filters, setFilters] = useState<KaryawanFilters>(emptyFilters)
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

  const lokasiOptions = useMemo(() => {
    const options = [...(lokasiList ?? [])]
      .sort((a, b) => a.nama.localeCompare(b.nama, 'id'))
      .map((loc) => ({ value: loc.id, label: loc.nama }))
    options.push({ value: NO_LOKASI, label: 'Tanpa lokasi' })
    return options
  }, [lokasiList])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return (karyawan ?? []).filter((k) => {
      if (q) {
        const hit =
          k.nama.toLowerCase().includes(q) ||
          k.karyawan_id.toLowerCase().includes(q) ||
          (k.jabatan ?? '').toLowerCase().includes(q)
        if (!hit) return false
      }
      if (!includesText(k.karyawan_id, filters.karyawan_id)) return false
      if (!includesText(k.nama, filters.nama)) return false
      if (filters.lokasi.length > 0) {
        const key = k.lokasi_kerja ?? NO_LOKASI
        if (!filters.lokasi.includes(key)) return false
      }
      if (!includesText(k.jabatan ?? '', filters.jabatan)) return false
      if (!includesText(k.wilayah ?? '', filters.wilayah)) return false
      if (filters.level.length > 0 && !filters.level.includes(k.level)) return false
      if (!inRange(k.cuti_tahunan, filters.cutiMin, filters.cutiMax)) return false
      if (!inRange(k.base_gaji ?? 0, filters.gajiMin, filters.gajiMax)) return false
      return true
    })
  }, [karyawan, search, filters])

  const activeFilters = countActiveFilters(filters)

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
    {
      key: 'base_gaji',
      title: COLUMN_LABELS.base_gaji,
      dataIndex: 'base_gaji',
      width: 160,
      render: (value: number) => formatCurrency(value ?? 0),
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
        await update.mutateAsync({ ...payload, karyawan_id: editingId })
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
          <Badge count={activeFilters} size="small">
            <Popover
              trigger="click"
              placement="bottomRight"
              content={
                <FilterFields
                  filters={filters}
                  setFilters={setFilters}
                  lokasiOptions={lokasiOptions}
                />
              }
            >
              <Button icon={<FilterOutlined />}>Filter</Button>
            </Popover>
          </Badge>
          <Dropdown
            trigger={['click']}
            popupRender={() => (
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
            <Button icon={<SettingOutlined />}>Kolom</Button>
          </Dropdown>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Tambah Karyawan
          </Button>
        </Space>
      </Space>

      {activeFilters > 0 ? (
        <Space wrap size={[4, 8]} style={{ marginTop: -8, marginBottom: 16 }}>
          {filters.karyawan_id.trim() ? (
            <Tag
              closable
              onClose={() => setFilters((prev) => ({ ...prev, karyawan_id: '' }))}
            >
              {COLUMN_LABELS.karyawan_id}: {filters.karyawan_id.trim()}
            </Tag>
          ) : null}
          {filters.nama.trim() ? (
            <Tag closable onClose={() => setFilters((prev) => ({ ...prev, nama: '' }))}>
              {COLUMN_LABELS.nama}: {filters.nama.trim()}
            </Tag>
          ) : null}
          {filters.lokasi.length > 0 ? (
            <Tag closable onClose={() => setFilters((prev) => ({ ...prev, lokasi: [] }))}>
              {COLUMN_LABELS.lokasi_kerja}:{' '}
              {filters.lokasi
                .map((id) =>
                  id === NO_LOKASI ? 'Tanpa lokasi' : (lokasiMap.get(id) ?? id),
                )
                .join(', ')}
            </Tag>
          ) : null}
          {filters.jabatan.trim() ? (
            <Tag closable onClose={() => setFilters((prev) => ({ ...prev, jabatan: '' }))}>
              {COLUMN_LABELS.jabatan}: {filters.jabatan.trim()}
            </Tag>
          ) : null}
          {filters.wilayah.trim() ? (
            <Tag closable onClose={() => setFilters((prev) => ({ ...prev, wilayah: '' }))}>
              {COLUMN_LABELS.wilayah}: {filters.wilayah.trim()}
            </Tag>
          ) : null}
          {filters.level.length > 0 ? (
            <Tag closable onClose={() => setFilters((prev) => ({ ...prev, level: [] }))}>
              {COLUMN_LABELS.level}:{' '}
              {[...filters.level].sort((a, b) => a - b).join(', ')}
            </Tag>
          ) : null}
          {filters.cutiMin != null || filters.cutiMax != null ? (
            <Tag
              closable
              onClose={() =>
                setFilters((prev) => ({ ...prev, cutiMin: null, cutiMax: null }))
              }
            >
              {COLUMN_LABELS.cuti_tahunan}: {rangeLabel(filters.cutiMin, filters.cutiMax)}
            </Tag>
          ) : null}
          {filters.gajiMin != null || filters.gajiMax != null ? (
            <Tag
              closable
              onClose={() =>
                setFilters((prev) => ({ ...prev, gajiMin: null, gajiMax: null }))
              }
            >
              {COLUMN_LABELS.base_gaji}:{' '}
              {rangeLabel(filters.gajiMin, filters.gajiMax, formatCurrency)}
            </Tag>
          ) : null}
          <Button type="link" size="small" onClick={() => setFilters(emptyFilters())}>
            Reset
          </Button>
        </Space>
      ) : null}

      <Table<Karyawan>
        rowKey="karyawan_id"
        size="small"
        loading={isLoading}
        dataSource={filtered}
        columns={columns}
        scroll={{ x: true }}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        locale={{
          emptyText:
            (karyawan?.length ?? 0) > 0
              ? 'Tidak ada karyawan yang cocok.'
              : 'Tidak ada data',
        }}
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

import { useMemo, useState, type Dispatch, type SetStateAction } from 'react'
import { EditOutlined, FilterOutlined } from '@ant-design/icons'
import {
  App,
  Alert,
  Badge,
  Button,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Popover,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import axios from 'axios'
import { useGajiKaryawan, useUpdateGajiKaryawan } from '../api/hooks'
import type { GajiKaryawan } from '../api/types'
import { formatCurrency } from '../constants'

const LEVEL_OPTIONS = Array.from({ length: 10 }, (_, level) => ({
  value: level,
  label: String(level),
}))

const ABSENSI_OPTIONS = [
  { value: 'ya', label: 'Ya' },
  { value: 'tidak', label: 'Tidak' },
]

const FIELD_LABELS = {
  karyawan_id: 'ID Karyawan',
  nama: 'Nama',
  level: 'Level',
  jabatan: 'Jabatan',
  no_bpjs: 'No. BPJS',
  base_gaji: 'Base Gaji',
  gaji_bulanan: 'Gaji Bulanan',
  absensi_dihitung: 'Absensi dihitung',
} as const

interface GajiKaryawanFilters {
  karyawan_id: string
  nama: string
  level: number[]
  jabatan: string
  no_bpjs: string
  baseMin: number | null
  baseMax: number | null
  bulananMin: number | null
  bulananMax: number | null
  absensi: Array<'ya' | 'tidak'>
}

interface GajiKaryawanFormValues {
  nama: string
  level: number
  jabatan?: string
  no_bpjs?: string
  base_gaji: number | null
  gaji_bulanan: number | null
  absensi_dihitung: boolean
}

function emptyFilters(): GajiKaryawanFilters {
  return {
    karyawan_id: '',
    nama: '',
    level: [],
    jabatan: '',
    no_bpjs: '',
    baseMin: null,
    baseMax: null,
    bulananMin: null,
    bulananMax: null,
    absensi: [],
  }
}

function includesText(value: string, query: string) {
  const needle = query.trim().toLowerCase()
  if (!needle) return true
  return value.toLowerCase().includes(needle)
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

function toNumberOrNull(value: number | string | null): number | null {
  if (value == null || value === '') return null
  const number = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(number) ? number : null
}

function countActiveFilters(filters: GajiKaryawanFilters) {
  let count = 0
  if (filters.karyawan_id.trim()) count += 1
  if (filters.nama.trim()) count += 1
  if (filters.level.length > 0) count += 1
  if (filters.jabatan.trim()) count += 1
  if (filters.no_bpjs.trim()) count += 1
  if (filters.baseMin != null || filters.baseMax != null) count += 1
  if (filters.bulananMin != null || filters.bulananMax != null) count += 1
  if (filters.absensi.length > 0) count += 1
  return count
}

function blank(value: string) {
  return value.trim() ? value : '—'
}

function errorMessage(err: unknown) {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail) return detail
  }
  return 'Gagal menyimpan karyawan.'
}

function integerRule(label: string) {
  return {
    validator: (_: unknown, value: number | null) => {
      if (value == null) return Promise.reject(new Error(`${label} wajib diisi`))
      if (!Number.isInteger(value) || value < 0) {
        return Promise.reject(new Error(`${label} harus bilangan bulat non-negatif`))
      }
      return Promise.resolve()
    },
  }
}

function TextFilter({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div>
      <Typography.Text style={{ fontSize: 12 }}>{label}</Typography.Text>
      <Input
        size="small"
        allowClear
        placeholder="Mengandung"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        style={{ marginTop: 4 }}
      />
    </div>
  )
}

function RangeFilter({
  label,
  min,
  max,
  onChange,
}: {
  label: string
  min: number | null
  max: number | null
  onChange: (min: number | null, max: number | null) => void
}) {
  return (
    <div>
      <Typography.Text style={{ fontSize: 12 }}>{label}</Typography.Text>
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <InputNumber
          size="small"
          min={0}
          precision={0}
          controls={false}
          placeholder="Min"
          value={min}
          onChange={(value) => onChange(toNumberOrNull(value), max)}
          style={{ flex: 1, width: '100%' }}
        />
        <InputNumber
          size="small"
          min={0}
          precision={0}
          controls={false}
          placeholder="Maks"
          value={max}
          onChange={(value) => onChange(min, toNumberOrNull(value))}
          style={{ flex: 1, width: '100%' }}
        />
      </div>
      {rangeInvalid(min, max) ? (
        <Typography.Text type="danger" style={{ fontSize: 12 }}>
          Minimum melebihi maksimum.
        </Typography.Text>
      ) : null}
    </div>
  )
}

function FilterFields({
  filters,
  setFilters,
}: {
  filters: GajiKaryawanFilters
  setFilters: Dispatch<SetStateAction<GajiKaryawanFilters>>
}) {
  const patch = (partial: Partial<GajiKaryawanFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }))
  }

  return (
    <div style={{ width: 280, maxHeight: 'min(70vh, 520px)', overflowY: 'auto' }}>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        Saring data
      </Typography.Text>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
        <TextFilter
          label={FIELD_LABELS.karyawan_id}
          value={filters.karyawan_id}
          onChange={(karyawan_id) => patch({ karyawan_id })}
        />
        <TextFilter
          label={FIELD_LABELS.nama}
          value={filters.nama}
          onChange={(nama) => patch({ nama })}
        />
        <div>
          <Typography.Text style={{ fontSize: 12 }}>{FIELD_LABELS.level}</Typography.Text>
          <Checkbox.Group
            style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 12px', marginTop: 4 }}
            value={filters.level}
            options={LEVEL_OPTIONS}
            onChange={(vals) => patch({ level: vals as number[] })}
          />
        </div>
        <TextFilter
          label={FIELD_LABELS.jabatan}
          value={filters.jabatan}
          onChange={(jabatan) => patch({ jabatan })}
        />
        <TextFilter
          label={FIELD_LABELS.no_bpjs}
          value={filters.no_bpjs}
          onChange={(no_bpjs) => patch({ no_bpjs })}
        />
        <RangeFilter
          label={FIELD_LABELS.base_gaji}
          min={filters.baseMin}
          max={filters.baseMax}
          onChange={(baseMin, baseMax) => patch({ baseMin, baseMax })}
        />
        <RangeFilter
          label={FIELD_LABELS.gaji_bulanan}
          min={filters.bulananMin}
          max={filters.bulananMax}
          onChange={(bulananMin, bulananMax) => patch({ bulananMin, bulananMax })}
        />
        <div>
          <Typography.Text style={{ fontSize: 12 }}>
            {FIELD_LABELS.absensi_dihitung}
          </Typography.Text>
          <Checkbox.Group
            style={{ display: 'flex', gap: 12, marginTop: 4 }}
            value={filters.absensi}
            options={ABSENSI_OPTIONS}
            onChange={(vals) => patch({ absensi: vals as Array<'ya' | 'tidak'> })}
          />
        </div>
        <Button
          size="small"
          disabled={countActiveFilters(filters) === 0}
          onClick={() => setFilters(emptyFilters())}
        >
          Reset
        </Button>
      </div>
    </div>
  )
}

function matchesFilters(row: GajiKaryawan, filters: GajiKaryawanFilters) {
  if (!includesText(row.karyawan_id, filters.karyawan_id)) return false
  if (!includesText(row.nama, filters.nama)) return false
  if (filters.level.length > 0 && !filters.level.includes(row.level)) return false
  if (!includesText(row.jabatan, filters.jabatan)) return false
  if (!includesText(row.no_bpjs, filters.no_bpjs)) return false
  if (!inRange(row.base_gaji, filters.baseMin, filters.baseMax)) return false
  if (!inRange(row.gaji_bulanan, filters.bulananMin, filters.bulananMax)) return false
  if (filters.absensi.length === 1) {
    const wantsCounted = filters.absensi[0] === 'ya'
    if (row.absensi_dihitung !== wantsCounted) return false
  }
  return true
}

export function GajiKaryawanTab() {
  const { message } = App.useApp()
  const { data, isLoading, isError } = useGajiKaryawan()
  const update = useUpdateGajiKaryawan()
  const [filters, setFilters] = useState<GajiKaryawanFilters>(emptyFilters)
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<GajiKaryawan | null>(null)
  const [form] = Form.useForm<GajiKaryawanFormValues>()

  const setFiltersAndResetPage: Dispatch<SetStateAction<GajiKaryawanFilters>> = (action) => {
    setFilters(action)
    setPage(1)
  }

  const filtered = useMemo(
    () => (data ?? []).filter((row) => matchesFilters(row, filters)),
    [data, filters],
  )
  const activeFilters = countActiveFilters(filters)

  const openEdit = (record: GajiKaryawan) => {
    setEditing(record)
    form.setFieldsValue({
      nama: record.nama,
      level: record.level,
      jabatan: record.jabatan,
      no_bpjs: record.no_bpjs,
      base_gaji: record.base_gaji,
      gaji_bulanan: record.gaji_bulanan,
      absensi_dihitung: record.absensi_dihitung,
    })
  }

  const handleSubmit = async () => {
    if (editing == null) return
    let values: GajiKaryawanFormValues
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    try {
      await update.mutateAsync({
        karyawan_id: editing.karyawan_id,
        nama: values.nama.trim(),
        level: values.level,
        jabatan: (values.jabatan ?? '').trim(),
        no_bpjs: (values.no_bpjs ?? '').trim(),
        base_gaji: values.base_gaji ?? 0,
        gaji_bulanan: values.gaji_bulanan ?? 0,
        absensi_dihitung: values.absensi_dihitung,
      })
      message.success('Karyawan diperbarui')
      setEditing(null)
    } catch (err) {
      message.error(errorMessage(err))
    }
  }

  const columns: ColumnsType<GajiKaryawan> = [
    { title: FIELD_LABELS.karyawan_id, dataIndex: 'karyawan_id', width: 120 },
    { title: FIELD_LABELS.nama, dataIndex: 'nama', width: 180 },
    { title: FIELD_LABELS.level, dataIndex: 'level', width: 80 },
    {
      title: FIELD_LABELS.jabatan,
      dataIndex: 'jabatan',
      width: 160,
      render: (value: string) => blank(value),
    },
    {
      title: FIELD_LABELS.no_bpjs,
      dataIndex: 'no_bpjs',
      width: 180,
      render: (value: string) => blank(value),
    },
    {
      title: FIELD_LABELS.base_gaji,
      dataIndex: 'base_gaji',
      width: 160,
      align: 'right',
      render: (value: number) => formatCurrency(value),
    },
    {
      title: FIELD_LABELS.gaji_bulanan,
      dataIndex: 'gaji_bulanan',
      width: 160,
      align: 'right',
      render: (value: number) => formatCurrency(value),
    },
    {
      title: FIELD_LABELS.absensi_dihitung,
      dataIndex: 'absensi_dihitung',
      width: 150,
      render: (value: boolean) => (value ? 'Ya' : 'Tidak'),
    },
    {
      key: 'aksi',
      title: 'Aksi',
      width: 90,
      fixed: 'right',
      render: (_, record) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
          Edit
        </Button>
      ),
    },
  ]

  if (isError) {
    return <Alert type="error" showIcon message="Gagal memuat daftar karyawan." />
  }

  return (
    <>
      <Space wrap style={{ marginBottom: 16 }}>
        <Badge count={activeFilters} size="small">
          <Popover
            trigger="click"
            placement="bottomLeft"
            content={<FilterFields filters={filters} setFilters={setFiltersAndResetPage} />}
          >
            <Button icon={<FilterOutlined />}>Filter</Button>
          </Popover>
        </Badge>
      </Space>

      {activeFilters > 0 ? (
        <Space wrap size={[4, 8]} style={{ marginTop: -8, marginBottom: 16 }}>
          {filters.karyawan_id.trim() ? (
            <Tag
              closable
              onClose={() => setFiltersAndResetPage((prev) => ({ ...prev, karyawan_id: '' }))}
            >
              {FIELD_LABELS.karyawan_id}: {filters.karyawan_id.trim()}
            </Tag>
          ) : null}
          {filters.nama.trim() ? (
            <Tag closable onClose={() => setFiltersAndResetPage((prev) => ({ ...prev, nama: '' }))}>
              {FIELD_LABELS.nama}: {filters.nama.trim()}
            </Tag>
          ) : null}
          {filters.level.length > 0 ? (
            <Tag
              closable
              onClose={() => setFiltersAndResetPage((prev) => ({ ...prev, level: [] }))}
            >
              {FIELD_LABELS.level}: {[...filters.level].sort((a, b) => a - b).join(', ')}
            </Tag>
          ) : null}
          {filters.jabatan.trim() ? (
            <Tag
              closable
              onClose={() => setFiltersAndResetPage((prev) => ({ ...prev, jabatan: '' }))}
            >
              {FIELD_LABELS.jabatan}: {filters.jabatan.trim()}
            </Tag>
          ) : null}
          {filters.no_bpjs.trim() ? (
            <Tag
              closable
              onClose={() => setFiltersAndResetPage((prev) => ({ ...prev, no_bpjs: '' }))}
            >
              {FIELD_LABELS.no_bpjs}: {filters.no_bpjs.trim()}
            </Tag>
          ) : null}
          {filters.baseMin != null || filters.baseMax != null ? (
            <Tag
              closable
              onClose={() =>
                setFiltersAndResetPage((prev) => ({ ...prev, baseMin: null, baseMax: null }))
              }
            >
              {FIELD_LABELS.base_gaji}: {rangeLabel(filters.baseMin, filters.baseMax, formatCurrency)}
            </Tag>
          ) : null}
          {filters.bulananMin != null || filters.bulananMax != null ? (
            <Tag
              closable
              onClose={() =>
                setFiltersAndResetPage((prev) => ({
                  ...prev,
                  bulananMin: null,
                  bulananMax: null,
                }))
              }
            >
              {FIELD_LABELS.gaji_bulanan}:{' '}
              {rangeLabel(filters.bulananMin, filters.bulananMax, formatCurrency)}
            </Tag>
          ) : null}
          {filters.absensi.length > 0 ? (
            <Tag
              closable
              onClose={() => setFiltersAndResetPage((prev) => ({ ...prev, absensi: [] }))}
            >
              {FIELD_LABELS.absensi_dihitung}:{' '}
              {filters.absensi.map((value) => (value === 'ya' ? 'Ya' : 'Tidak')).join(', ')}
            </Tag>
          ) : null}
          <Button type="link" size="small" onClick={() => setFiltersAndResetPage(emptyFilters())}>
            Reset
          </Button>
        </Space>
      ) : null}

      <Table<GajiKaryawan>
        rowKey="karyawan_id"
        size="small"
        loading={isLoading}
        dataSource={filtered}
        columns={columns}
        pagination={{
          current: page,
          pageSize: 20,
          showSizeChanger: false,
          onChange: setPage,
        }}
        scroll={{ x: true }}
        locale={{
          emptyText:
            (data?.length ?? 0) > 0 ? 'Tidak ada karyawan yang cocok.' : 'Tidak ada data',
        }}
      />

      <Modal
        title="Edit Karyawan"
        open={editing != null}
        onCancel={() => setEditing(null)}
        destroyOnHidden
        width={520}
        footer={
          <Space>
            <Button onClick={() => setEditing(null)}>Batal</Button>
            <Button type="primary" loading={update.isPending} onClick={handleSubmit}>
              Simpan
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" requiredMark="optional" onFinish={handleSubmit}>
          <Form.Item label={FIELD_LABELS.karyawan_id}>
            <Input value={editing?.karyawan_id} disabled />
          </Form.Item>
          <Form.Item
            name="nama"
            label={FIELD_LABELS.nama}
            rules={[
              { required: true, whitespace: true, message: 'Nama wajib diisi' },
              { max: 128, message: 'Maksimal 128 karakter' },
            ]}
          >
            <Input maxLength={128} />
          </Form.Item>
          <Form.Item
            name="level"
            label={FIELD_LABELS.level}
            rules={[{ required: true, message: 'Level wajib dipilih' }]}
          >
            <Select options={LEVEL_OPTIONS} />
          </Form.Item>
          <Form.Item
            name="jabatan"
            label={FIELD_LABELS.jabatan}
            rules={[{ max: 128, message: 'Maksimal 128 karakter' }]}
          >
            <Input maxLength={128} />
          </Form.Item>
          <Form.Item
            name="no_bpjs"
            label={FIELD_LABELS.no_bpjs}
            rules={[{ max: 16, message: 'Maksimal 16 karakter' }]}
          >
            <Input maxLength={16} />
          </Form.Item>
          <Form.Item
            name="base_gaji"
            label={FIELD_LABELS.base_gaji}
            rules={[integerRule('Base gaji')]}
          >
            <InputNumber min={0} precision={0} controls={false} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="gaji_bulanan"
            label={FIELD_LABELS.gaji_bulanan}
            rules={[integerRule('Gaji bulanan')]}
          >
            <InputNumber min={0} precision={0} controls={false} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="absensi_dihitung"
            label={FIELD_LABELS.absensi_dihitung}
            valuePropName="checked"
          >
            <Switch checkedChildren="Ya" unCheckedChildren="Tidak" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

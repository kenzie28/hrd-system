import { useState, type CSSProperties } from 'react'
import { InboxOutlined, UploadOutlined } from '@ant-design/icons'
import {
  App as AntApp,
  Alert,
  Button,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import { useKaryawanUpdateImport } from '../api/hooks'
import type { KaryawanImportResult } from '../api/types'

function hasHeaderErrors(result: KaryawanImportResult) {
  return result.errors.some((e) => e.row === 0)
}

function failureSummary(result: KaryawanImportResult) {
  if (result.errors.length === 1) {
    return result.errors[0].message
  }
  if (hasHeaderErrors(result)) {
    return 'Validasi header gagal — periksa kolom wajib dan header yang diterima di bawah.'
  }
  return `Validasi data gagal pada ${result.errors.length} baris — tidak ada data disimpan.`
}

function ImportResultPanel({ result }: { result: KaryawanImportResult }) {
  if (result.ok) {
    return (
      <Alert
        type="success"
        showIcon
        message="Update berhasil"
        description={
          <>
            Total baris: {result.total_rows}, diperbarui: {result.updated}
          </>
        }
      />
    )
  }

  return (
    <>
      <Alert
        type="error"
        showIcon
        message="Update gagal"
        description={
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Typography.Text>{failureSummary(result)}</Typography.Text>
            {result.total_rows > 0 && (
              <Typography.Text type="secondary">
                Total baris diproses: {result.total_rows}. Tidak ada baris yang diubah.
              </Typography.Text>
            )}
          </Space>
        }
      />

      {result.required_columns.length > 0 && hasHeaderErrors(result) && (
        <Alert
          style={{ marginTop: 16 }}
          type="warning"
          showIcon
          message="Kolom wajib"
          description={
            <Space size={[4, 4]} wrap>
              {result.required_columns.map((col) => (
                <Tag key={col}>{col}</Tag>
              ))}
            </Space>
          }
        />
      )}

      {result.optional_columns.length > 0 && hasHeaderErrors(result) && (
        <Alert
          style={{ marginTop: 16 }}
          type="warning"
          showIcon
          message="Kolom opsional (sertakan hanya field yang ingin diubah)"
          description={
            <Space size={[4, 4]} wrap>
              {result.optional_columns.map((col) => (
                <Tag key={col}>{col}</Tag>
              ))}
            </Space>
          }
        />
      )}

      {result.received_headers.length > 0 && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          showIcon
          message="Header yang diterima dari file"
          description={
            <Typography.Paragraph
              copyable
              style={{ marginBottom: 0, fontFamily: 'monospace', fontSize: 12 }}
            >
              {result.received_headers.join(', ')}
            </Typography.Paragraph>
          }
        />
      )}

      {result.errors.length > 0 && (
        <Table
          style={{ marginTop: 16 }}
          rowKey={(r) => `${r.row}-${r.message}`}
          size="small"
          pagination={{ pageSize: 20 }}
          dataSource={result.errors}
          columns={[
            {
              title: 'Baris',
              dataIndex: 'row',
              width: 90,
              render: (row: number) => (row === 0 ? 'Header' : row),
            },
            { title: 'Pesan error', dataIndex: 'message' },
          ]}
        />
      )}
    </>
  )
}

const EXAMPLE_HEADERS = ['karyawan_id', 'jabatan', 'cuti_tahunan'] as const

const EXAMPLE_ROWS = [
  {
    row: 1,
    values: [...EXAMPLE_HEADERS],
    isHeader: true,
  },
  {
    row: 2,
    values: ['0000003', 'Director', '14'],
    isHeader: false,
  },
  {
    row: 3,
    values: ['0000010', 'SPG', '12'],
    isHeader: false,
  },
] as const

const COL_LETTERS = ['A', 'B', 'C']

const sheetCell: CSSProperties = {
  border: '1px solid #d0d7de',
  padding: '6px 10px',
  fontSize: 13,
  lineHeight: 1.4,
  textAlign: 'left',
  whiteSpace: 'nowrap',
}

const sheetCorner: CSSProperties = {
  ...sheetCell,
  background: '#e8eaed',
  width: 36,
  minWidth: 36,
  textAlign: 'center',
  color: '#5f6368',
  fontSize: 11,
  fontWeight: 500,
  userSelect: 'none',
}

const sheetColHeader: CSSProperties = {
  ...sheetCorner,
  width: 'auto',
  minWidth: 100,
}

function ContohSheet() {
  return (
    <div style={{ marginBottom: 16, overflowX: 'auto' }}>
      <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
        Contoh format (hanya kolom yang disertakan yang diubah)
      </Typography.Text>
      <table
        style={{
          borderCollapse: 'collapse',
          background: '#fff',
          boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
          maxWidth: '100%',
        }}
      >
        <thead>
          <tr>
            <th style={sheetCorner} />
            {COL_LETTERS.map((letter) => (
              <th key={letter} style={sheetColHeader}>
                {letter}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {EXAMPLE_ROWS.map((r) => (
            <tr key={r.row}>
              <th style={sheetCorner}>{r.row}</th>
              {r.values.map((cell, i) => (
                <td
                  key={i}
                  style={{
                    ...sheetCell,
                    fontWeight: r.isHeader ? 600 : 400,
                    background: r.isHeader ? '#f8f9fa' : '#fff',
                    fontFamily: r.isHeader
                      ? undefined
                      : 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                  }}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function UpdateKaryawanTab() {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<KaryawanImportResult | null>(null)
  const karyawanUpdateImport = useKaryawanUpdateImport()
  const { message } = AntApp.useApp()

  const uploadProps: UploadProps = {
    accept: '.csv',
    multiple: false,
    maxCount: 1,
    fileList,
    beforeUpload: (file) => {
      setSelectedFile(file)
      setResult(null)
      return false
    },
    onChange: ({ fileList: newFileList }) => {
      setFileList(newFileList.slice(-1))
    },
    onRemove: () => {
      setFileList([])
      setSelectedFile(null)
      setResult(null)
    },
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setResult(null)
    const data = await karyawanUpdateImport.mutateAsync({ file: selectedFile })
    setResult(data)
    if (data.ok) {
      message.success(`Update berhasil: ${data.updated} karyawan diperbarui.`)
    }
  }

  return (
    <div>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        Tab ini <Typography.Text strong>memperbarui karyawan yang sudah ada</Typography.Text>.
        Kolom <Typography.Text code>karyawan_id</Typography.Text> wajib dan harus sudah
        terdaftar. Kolom lain bersifat opsional — jika sebuah kolom ada di CSV, field
        itu diubah sesuai nilai pada setiap baris. Kolom opsional:{' '}
        <Typography.Text code>nama</Typography.Text>,{' '}
        <Typography.Text code>level</Typography.Text>,{' '}
        <Typography.Text code>jabatan</Typography.Text>,{' '}
        <Typography.Text code>wilayah</Typography.Text>,{' '}
        <Typography.Text code>lokasi_kerja</Typography.Text>,{' '}
        <Typography.Text code>cuti_tahunan</Typography.Text>. Untuk menambah karyawan
        baru, gunakan tab Tambah Karyawan (CSV).
      </Typography.Paragraph>

      <ContohSheet />

      <Upload.Dragger {...uploadProps} disabled={karyawanUpdateImport.isPending}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">Klik atau seret file CSV ke sini untuk memilih</p>
      </Upload.Dragger>

      <Space style={{ marginTop: 16 }}>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={handleUpload}
          disabled={!selectedFile}
          loading={karyawanUpdateImport.isPending}
        >
          Unggah
        </Button>
      </Space>

      {result && (
        <div style={{ marginTop: 24 }}>
          <ImportResultPanel result={result} />
        </div>
      )}
    </div>
  )
}

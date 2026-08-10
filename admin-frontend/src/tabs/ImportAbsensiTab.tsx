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
import { useAbsensiImport } from '../api/hooks'
import type { AbsensiImportResult } from '../api/types'

function hasHeaderErrors(result: AbsensiImportResult) {
  return result.errors.some((e) => e.row === 0)
}

function failureSummary(result: AbsensiImportResult) {
  if (result.errors.length === 1) {
    return result.errors[0].message
  }
  if (hasHeaderErrors(result)) {
    return 'Validasi header gagal — periksa kolom wajib dan header yang diterima di bawah.'
  }
  return `Validasi data gagal pada ${result.errors.length} baris — tidak ada data disimpan.`
}

function ImportResultPanel({ result }: { result: AbsensiImportResult }) {
  if (result.ok) {
    return (
      <Alert
        type="success"
        showIcon
        message="Import berhasil"
        description={
          <>
            Total baris: {result.total_rows}, dibuat: {result.created}
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
        message="Import gagal"
        description={
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Typography.Text>{failureSummary(result)}</Typography.Text>
            {result.total_rows > 0 && (
              <Typography.Text type="secondary">
                Total baris diproses: {result.total_rows}. Tidak ada baris yang disimpan.
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

const EXAMPLE_ROWS = [
  {
    row: 1,
    karyawan_id: 'karyawan_id',
    lokasi_kerja: 'lokasi_kerja',
    tanggal: 'tanggal',
    jam_masuk: 'jam_masuk',
    jam_keluar: 'jam_keluar',
    isHeader: true,
  },
  {
    row: 2,
    karyawan_id: '0000123',
    lokasi_kerja: '01',
    tanggal: '2026-08-01',
    jam_masuk: '08:00',
    jam_keluar: '16:00',
    isHeader: false,
  },
  {
    row: 3,
    karyawan_id: '0000123',
    lokasi_kerja: '01',
    tanggal: '2026-08-02',
    jam_masuk: '22:00',
    jam_keluar: '06:00',
    isHeader: false,
  },
] as const

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
  minWidth: 120,
}

function ContohSheet() {
  return (
    <div style={{ marginBottom: 16, overflowX: 'auto' }}>
      <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
        Contoh format (delimiter koma atau titik koma). Baris 3 adalah contoh shift malam —
        jam_keluar lebih kecil dari jam_masuk sehingga otomatis dihitung keluar di hari berikutnya.
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
            <th style={sheetColHeader}>A</th>
            <th style={sheetColHeader}>B</th>
            <th style={sheetColHeader}>C</th>
            <th style={sheetColHeader}>D</th>
            <th style={sheetColHeader}>E</th>
          </tr>
        </thead>
        <tbody>
          {EXAMPLE_ROWS.map((r) => (
            <tr key={r.row}>
              <th style={sheetCorner}>{r.row}</th>
              {[r.karyawan_id, r.lokasi_kerja, r.tanggal, r.jam_masuk, r.jam_keluar].map(
                (value, i) => (
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
                    {value}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ImportAbsensiTab() {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<AbsensiImportResult | null>(null)
  const absensiImport = useAbsensiImport()
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
    const data = await absensiImport.mutateAsync({ file: selectedFile })
    setResult(data)
    if (data.ok) {
      message.success(`Import berhasil: ${data.created} absensi dibuat.`)
    }
  }

  return (
    <div>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        Unggah file CSV dengan kolom <Typography.Text code>karyawan_id</Typography.Text> (ID
        karyawan), <Typography.Text code>lokasi_kerja</Typography.Text> (kode lokasi),{' '}
        <Typography.Text code>tanggal</Typography.Text> (format{' '}
        <Typography.Text code>yyyy-mm-dd</Typography.Text>),{' '}
        <Typography.Text code>jam_masuk</Typography.Text>, dan{' '}
        <Typography.Text code>jam_keluar</Typography.Text> (format{' '}
        <Typography.Text code>HH:MM</Typography.Text>). Untuk shift yang keluar di hari
        berikutnya, cukup isi jam_keluar lebih kecil dari jam_masuk.
      </Typography.Paragraph>

      <ContohSheet />

      <Upload.Dragger {...uploadProps} disabled={absensiImport.isPending}>
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
          loading={absensiImport.isPending}
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

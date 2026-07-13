import { useState } from 'react'
import { InboxOutlined, UploadOutlined } from '@ant-design/icons'
import {
  App as AntApp,
  Alert,
  Button,
  Checkbox,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import { useGajiImport } from '../api/hooks'
import type { GajiImportResult } from '../api/types'

function hasHeaderErrors(result: GajiImportResult) {
  return result.errors.some((e) => e.row === 0)
}

function failureSummary(result: GajiImportResult) {
  if (result.errors.length === 1) {
    return result.errors[0].message
  }
  if (hasHeaderErrors(result)) {
    return 'Validasi header gagal — periksa kolom wajib dan header yang diterima di bawah.'
  }
  return `Validasi data gagal pada ${result.errors.length} baris — tidak ada data disimpan.`
}

function ImportResultPanel({ result }: { result: GajiImportResult }) {
  if (result.ok) {
    return (
      <Alert
        type="success"
        showIcon
        message="Import berhasil"
        description={
          <>
            Total baris: {result.total_rows}, dibuat: {result.created}, diperbarui:{' '}
            {result.updated}, karyawan baru: {result.karyawan_created}
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

export function ImportGajiTab() {
  const [upsertKaryawan, setUpsertKaryawan] = useState(true)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<GajiImportResult | null>(null)
  const gajiImport = useGajiImport()
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
    const data = await gajiImport.mutateAsync({ file: selectedFile, upsertKaryawan })
    setResult(data)
    if (data.ok) {
      message.success(`Import berhasil: ${data.created} dibuat, ${data.updated} diperbarui.`)
    }
  }

  return (
    <div>
      <Typography.Paragraph type="secondary">
        Unggah file CSV gaji bulanan (format sama seperti <code>gaji-input.csv</code>). Setiap
        baris akan dicocokkan ke karyawan berdasarkan kolom <code>NO.ID</code>.
      </Typography.Paragraph>

      <Checkbox
        checked={upsertKaryawan}
        onChange={(e) => setUpsertKaryawan(e.target.checked)}
        style={{ marginBottom: 16 }}
      >
        Upsert data karyawan dari CSV (nama, jabatan, lokasi kerja, level dari kolom Gol —
        buat karyawan baru dengan level 1 jika Gol kosong).{' '}
        <strong>Fitur sementara untuk testing, akan dihapus.</strong>
      </Checkbox>

      <Upload.Dragger {...uploadProps} disabled={gajiImport.isPending}>
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
          loading={gajiImport.isPending}
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

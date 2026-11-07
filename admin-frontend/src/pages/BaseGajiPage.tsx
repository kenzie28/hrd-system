import { useState } from 'react'
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
import { useBaseGajiImport } from '../api/hooks'
import type { KaryawanImportResult } from '../api/types'
import { ImportErrorCsvDownload } from '../components/ImportErrorCsvDownload'

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
        message="Import berhasil"
        description={
          <>
            Total baris: {result.total_rows}, karyawan diperbarui: {result.updated}
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
                Total baris diproses: {result.total_rows}. Tidak ada karyawan yang diubah.
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
        <>
          <ImportErrorCsvDownload errors={result.errors} />
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
        </>
      )}
    </>
  )
}

export default function BaseGajiPage() {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<KaryawanImportResult | null>(null)
  const baseGajiImport = useBaseGajiImport()
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
    const data = await baseGajiImport.mutateAsync({ file: selectedFile })
    setResult(data)
    if (data.ok) {
      message.success(`Import berhasil: ${data.updated} karyawan diperbarui.`)
    }
  }

  return (
    <div>
      <Typography.Title level={3}>Base Gaji</Typography.Title>
      <Typography.Paragraph type="secondary">
        Modul sementara. Unggah CSV dengan kolom <Typography.Text code>jabatan</Typography.Text>{' '}
        dan <Typography.Text code>base_gaji</Typography.Text>. Jabatan dicocokkan persis
        (huruf besar/kecil dan spasi di tengah harus sama). Setiap karyawan dengan jabatan itu
        diisi <Typography.Text code>base_gaji</Typography.Text>-nya. Jabatan yang tidak ada,
        atau yang muncul dua kali, membuat seluruh file ditolak.
      </Typography.Paragraph>
      <Typography.Paragraph>
        <pre style={{ margin: 0 }}>
          {`jabatan,base_gaji
Staff,4500000
Staff Senior,8000000`}
        </pre>
      </Typography.Paragraph>

      <Upload.Dragger {...uploadProps} disabled={baseGajiImport.isPending}>
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
          loading={baseGajiImport.isPending}
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

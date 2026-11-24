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
import { useBaseGajiImport, useGajiBulananImport } from '../api/hooks'
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

interface WageImport {
  isPending: boolean
  mutateAsync: (vars: { file: File }) => Promise<KaryawanImportResult>
}

interface WageCsvImportTabProps {
  description: string
  example: string
  columnName: string
  wageImport: WageImport
}

function WageCsvImportTab({
  description,
  example,
  columnName,
  wageImport,
}: WageCsvImportTabProps) {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<KaryawanImportResult | null>(null)
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
    const data = await wageImport.mutateAsync({ file: selectedFile })
    setResult(data)
    if (data.ok) {
      message.success(`Import berhasil: ${data.updated} karyawan diperbarui.`)
    }
  }

  return (
    <div>
      <Typography.Paragraph type="secondary">{description}</Typography.Paragraph>
      <Typography.Paragraph>
        Setiap baris mengisi <Typography.Text code>{columnName}</Typography.Text> untuk satu
        karyawan. <Typography.Text code>karyawan_id</Typography.Text> yang tidak ada, atau yang
        muncul dua kali, membuat seluruh file ditolak.
      </Typography.Paragraph>
      <Typography.Paragraph>
        <pre style={{ margin: 0 }}>{example}</pre>
      </Typography.Paragraph>

      <Upload.Dragger {...uploadProps} disabled={wageImport.isPending}>
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
          loading={wageImport.isPending}
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

export function ImportBaseGajiTab() {
  const wageImport = useBaseGajiImport()
  return (
    <WageCsvImportTab
      columnName="base_gaji"
      description="Unggah CSV untuk mengisi base gaji tiap karyawan."
      example={'karyawan_id,base_gaji\n1000001,4500000\n1000002,8000000'}
      wageImport={wageImport}
    />
  )
}

export function ImportGajiBulananTab() {
  const wageImport = useGajiBulananImport()
  return (
    <WageCsvImportTab
      columnName="gaji_bulanan"
      description="Unggah CSV untuk mengisi gaji bulanan tiap karyawan."
      example={'karyawan_id,gaji_bulanan\n1000001,5000000\n1000002,9000000'}
      wageImport={wageImport}
    />
  )
}

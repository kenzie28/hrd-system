import { InboxOutlined, UploadOutlined } from '@ant-design/icons'
import { App as AntApp, Button, Space, Typography, Upload } from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import { useState, type CSSProperties } from 'react'
import { useCutiImport, useCutiSakitImport } from '../api/hooks'
import type { CutiImportResult } from '../api/types'
import { ImportResultPanel } from './ImportAbsensiTab'

interface ImportAction {
  isPending: boolean
  mutateAsync: (variables: { file: File }) => Promise<CutiImportResult>
}

const cellStyle: CSSProperties = {
  border: '1px solid #d0d7de',
  padding: '6px 10px',
  fontSize: 13,
  textAlign: 'left',
  whiteSpace: 'nowrap',
}

function ExampleSheet() {
  return (
    <div style={{ marginBottom: 16, overflowX: 'auto' }}>
      <Typography.Text
        type="secondary"
        style={{ display: 'block', fontSize: 12, marginBottom: 8 }}
      >
        Contoh format (delimiter koma atau titik koma).
      </Typography.Text>
      <table style={{ borderCollapse: 'collapse', background: '#fff' }}>
        <thead>
          <tr>
            <th style={{ ...cellStyle, background: '#e8eaed' }} />
            <th style={{ ...cellStyle, background: '#e8eaed' }}>A</th>
            <th style={{ ...cellStyle, background: '#e8eaed' }}>B</th>
          </tr>
        </thead>
        <tbody>
          {[
            ['1', 'karyawan_id', 'tanggal'],
            ['2', '0000123', '2026-08-01'],
            ['3', '0000456', '2026-08-02'],
          ].map(([row, employeeId, date], index) => (
            <tr key={row}>
              <th style={{ ...cellStyle, background: '#e8eaed' }}>{row}</th>
              <td
                style={{
                  ...cellStyle,
                  fontWeight: index === 0 ? 600 : 400,
                  fontFamily: index === 0 ? undefined : 'monospace',
                }}
              >
                {employeeId}
              </td>
              <td
                style={{
                  ...cellStyle,
                  fontWeight: index === 0 ? 600 : 400,
                  fontFamily: index === 0 ? undefined : 'monospace',
                }}
              >
                {date}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ImportCutiForm({
  label,
  importAction,
}: {
  label: 'Cuti' | 'Sakit'
  importAction: ImportAction
}) {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<CutiImportResult | null>(null)
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
    onChange: ({ fileList: nextFiles }) => setFileList(nextFiles.slice(-1)),
    onRemove: () => {
      setFileList([])
      setSelectedFile(null)
      setResult(null)
    },
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    setResult(null)
    const data = await importAction.mutateAsync({ file: selectedFile })
    setResult(data)
    if (data.ok) {
      message.success(`Import berhasil: ${data.created} hari ${label.toLowerCase()} dibuat.`)
    }
  }

  return (
    <div>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        Unggah file CSV dengan kolom <Typography.Text code>karyawan_id</Typography.Text>{' '}
        dan <Typography.Text code>tanggal</Typography.Text> (format{' '}
        <Typography.Text code>yyyy-mm-dd</Typography.Text>). Setiap baris akan membuat
        permohonan {label.toLowerCase()} satu hari yang langsung berstatus approved.
      </Typography.Paragraph>

      <ExampleSheet />

      <Upload.Dragger {...uploadProps} disabled={importAction.isPending}>
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
          loading={importAction.isPending}
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

export function ImportCutiTab() {
  const importAction = useCutiImport()
  return <ImportCutiForm label="Cuti" importAction={importAction} />
}

export function ImportSakitTab() {
  const importAction = useCutiSakitImport()
  return <ImportCutiForm label="Sakit" importAction={importAction} />
}

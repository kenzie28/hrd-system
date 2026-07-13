import { useState } from 'react'
import { InboxOutlined, UploadOutlined } from '@ant-design/icons'
import {
  App as AntApp,
  Alert,
  Button,
  Checkbox,
  Space,
  Table,
  Typography,
  Upload,
} from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import { useGajiImport } from '../api/hooks'
import type { GajiImportResult } from '../api/types'

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
    try {
      const data = await gajiImport.mutateAsync({ file: selectedFile, upsertKaryawan })
      setResult(data)
      if (data.ok) {
        message.success(`Import berhasil: ${data.created} dibuat, ${data.updated} diperbarui.`)
      } else {
        message.error('Import gagal, periksa daftar error di bawah.')
      }
    } catch {
      message.error('Gagal mengunggah file CSV.')
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
        Upsert data karyawan dari CSV (nama, jabatan, lokasi kerja — buat karyawan baru dengan
        level 1 jika belum ada). <strong>Fitur sementara untuk testing, akan dihapus.</strong>
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
          <Alert
            type={result.ok ? 'success' : 'error'}
            showIcon
            message={result.ok ? 'Import berhasil' : 'Import gagal — tidak ada data disimpan'}
            description={
              <>
                Total baris: {result.total_rows}, dibuat: {result.created}, diperbarui:{' '}
                {result.updated}, karyawan baru: {result.karyawan_created}
              </>
            }
          />
          {result.errors.length > 0 && (
            <Table
              style={{ marginTop: 16 }}
              rowKey={(r) => `${r.row}-${r.message}`}
              size="small"
              pagination={{ pageSize: 20 }}
              dataSource={result.errors}
              columns={[
                { title: 'Baris', dataIndex: 'row', width: 80 },
                { title: 'Error', dataIndex: 'message' },
              ]}
            />
          )}
        </div>
      )}
    </div>
  )
}

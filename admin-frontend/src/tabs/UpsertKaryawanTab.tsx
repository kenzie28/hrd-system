import { useState } from 'react'
import { InboxOutlined, UploadOutlined } from '@ant-design/icons'
import {
  App as AntApp,
  Alert,
  Button,
  Space,
  Table,
  Typography,
  Upload,
} from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import { useKaryawanUpsertImport } from '../api/hooks'
import type { KaryawanImportResult } from '../api/types'
import { ImportErrorCsvDownload } from '../components/ImportErrorCsvDownload'

const HO_COLUMNS = [
  'karyawan_id',
  'nama_karyawan',
  'level',
  'role',
  'status_kontrak',
  'percobaan_jabatan',
  'tanggal_kontrak_awal',
  'tanggal_kontrak_akhir',
  'tanggal_awal',
  'TG.LAHIR',
  'jenis_kelamin',
  'status_k_tk',
  'lokasi_kerja',
  'npwp',
  'no_bpjs',
  'no_kpj',
  'tanggal_kpj',
]

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
        message="Impor berhasil"
        description={
          <>
            Total baris: {result.total_rows}, ditambahkan: {result.created}, diperbarui:{' '}
            {result.updated}
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
        message="Impor gagal"
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
            pagination={{ pageSize: 8, showSizeChanger: false }}
            dataSource={result.errors}
            columns={[
              { title: 'Baris', dataIndex: 'row', width: 80 },
              { title: 'Pesan', dataIndex: 'message' },
            ]}
          />
        </>
      )}
    </>
  )
}

export function UpsertKaryawanTab() {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<KaryawanImportResult | null>(null)
  const karyawanUpsertImport = useKaryawanUpsertImport()
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
    const data = await karyawanUpsertImport.mutateAsync({ file: selectedFile })
    setResult(data)
    if (data.ok) {
      message.success(
        `Impor berhasil: ${data.created} ditambahkan, ${data.updated} diperbarui.`,
      )
    }
  }

  return (
    <div>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        Unggah file karyawan untuk menambah baris baru dan memperbarui karyawan yang
        sudah ada. Pencocokan memakai <Typography.Text code>karyawan_id</Typography.Text>.
        ID yang sudah terdaftar diperbarui. Gaji, cuti, wilayah, lembur, tanggal keluar,
        dan login portal tidak diubah.
      </Typography.Paragraph>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        Kolom file HO:{' '}
        {HO_COLUMNS.map((column, index) => (
          <span key={column}>
            {index > 0 ? ', ' : null}
            <Typography.Text code>{column}</Typography.Text>
          </span>
        ))}
        . Nama juga diterima sebagai <Typography.Text code>nama</Typography.Text>, jabatan
        sebagai <Typography.Text code>jabatan</Typography.Text>, tanggal lahir sebagai{' '}
        <Typography.Text code>tanggal_lahir</Typography.Text>, dan no. KPJ sebagai{' '}
        <Typography.Text code>kpj</Typography.Text>. Level 0–9. Tanggal boleh{' '}
        <Typography.Text code>YYYY-MM-DD</Typography.Text> atau{' '}
        <Typography.Text code>DD/MM/YYYY</Typography.Text>; sel{' '}
        <Typography.Text code>- -</Typography.Text> dikosongkan. Jenis kelamin{' '}
        <Typography.Text code>P</Typography.Text> atau <Typography.Text code>L</Typography.Text>.
        Percobaan jabatan <Typography.Text code>Y</Typography.Text> atau{' '}
        <Typography.Text code>N</Typography.Text>. Kode lokasi yang belum ada dibuat
        otomatis.
      </Typography.Paragraph>

      <Upload.Dragger {...uploadProps} disabled={karyawanUpsertImport.isPending}>
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
          loading={karyawanUpsertImport.isPending}
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

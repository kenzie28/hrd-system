import { useEffect, useState } from 'react'
import {
  DatabaseOutlined,
  DeleteOutlined,
  DownloadOutlined,
  InboxOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import {
  App as AntApp,
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Space,
  Table,
  Typography,
  Upload,
} from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import { useStateExport, useStateImport, useStateReset } from '../api/hooks'
import type { StateImportResult } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { ImportErrorCsvDownload } from '../components/ImportErrorCsvDownload'

const MODULE_PASSWORD = 'bears'
const PASSWORD_STORAGE_KEY = 'hrd_state_manager_password'

function readStoredPassword(): string {
  try {
    return sessionStorage.getItem(PASSWORD_STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

function storePassword(password: string) {
  try {
    sessionStorage.setItem(PASSWORD_STORAGE_KEY, password)
  } catch {
    /* ignore quota / private mode */
  }
}

function clearStoredPassword() {
  try {
    sessionStorage.removeItem(PASSWORD_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

async function errorDetail(err: unknown): Promise<string> {
  if (!axios.isAxiosError(err)) return 'Terjadi kesalahan.'
  const data = err.response?.data
  if (typeof Blob !== 'undefined' && data instanceof Blob) {
    const text = await data.text()
    try {
      const json = JSON.parse(text) as { detail?: string }
      if (json.detail) return json.detail
    } catch {
      if (text.trim()) return text
    }
  } else if (typeof data === 'object' && data !== null) {
    const record = data as { detail?: string }
    if (record.detail) return record.detail
  }
  if (err.response?.status === 403) {
    return 'Kata sandi State Manager tidak valid.'
  }
  return err.message || 'Terjadi kesalahan.'
}

function ImportResultPanel({ result }: { result: StateImportResult }) {
  if (result.ok) {
    const parts = Object.entries(result.counts)
      .map(([table, count]) => `${table}: ${count}`)
      .join(', ')
    return (
      <Alert
        type="success"
        showIcon
        message="State berhasil dipulihkan"
        description={parts || 'Semua tabel dipulihkan.'}
      />
    )
  }

  return (
    <>
      <Alert
        type="error"
        showIcon
        message="Pemulihan gagal"
        description="Tidak ada data yang diubah. Perbaiki file CSV lalu unggah lagi."
      />
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
            render: (row: number) => (row === 0 ? 'File' : row),
          },
          { title: 'Pesan error', dataIndex: 'message' },
        ]}
      />
    </>
  )
}

export default function StateManagerPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { logout } = useAuth()
  const { message, modal } = AntApp.useApp()
  const [unlocked, setUnlocked] = useState(() => readStoredPassword() === MODULE_PASSWORD)
  const [passwordForm] = Form.useForm<{ password: string }>()
  const [unlockError, setUnlockError] = useState<string | null>(null)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<StateImportResult | null>(null)

  const stateExport = useStateExport()
  const stateImport = useStateImport()
  const stateReset = useStateReset()

  useEffect(() => {
    if (!unlocked) {
      passwordForm.resetFields()
    }
  }, [unlocked, passwordForm])

  const goHome = () => navigate('/', { replace: true })

  const handleUnlock = async () => {
    const values = await passwordForm.validateFields()
    if (values.password !== MODULE_PASSWORD) {
      setUnlockError('Kata sandi salah.')
      return
    }
    storePassword(values.password)
    setUnlockError(null)
    setUnlocked(true)
  }

  const handleDownload = async () => {
    const password = readStoredPassword()
    try {
      const { blob, filename } = await stateExport.mutateAsync({ password })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      message.success('CSV state berhasil diunduh.')
    } catch (err) {
      message.error(await errorDetail(err))
    }
  }

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
    onChange: ({ fileList: next }) => {
      setFileList(next.slice(-1))
    },
    onRemove: () => {
      setFileList([])
      setSelectedFile(null)
      setResult(null)
    },
  }

  const runRestore = async () => {
    if (!selectedFile) return
    const password = readStoredPassword()
    setResult(null)
    const data = await stateImport.mutateAsync({ file: selectedFile, password })
    setResult(data)
    if (data.ok) {
      message.success('State berhasil dipulihkan. Silakan masuk kembali.')
      clearStoredPassword()
      logout()
      navigate('/login', { replace: true })
    }
  }

  const handleRestore = () => {
    if (!selectedFile) return
    modal.confirm({
      title: 'Ganti seluruh data HRD?',
      content:
        'Unggah ini menghapus data server saat ini dan menggantinya dengan isi file. Tindakan ini tidak bisa dibatalkan.',
      okText: 'Ganti data',
      okType: 'danger',
      cancelText: 'Batal',
      onOk: runRestore,
    })
  }

  const runReset = async () => {
    const password = readStoredPassword()
    try {
      await stateReset.mutateAsync({ password })
      queryClient.clear()
      message.success('Database berhasil direset.')
      navigate('/', { replace: true })
    } catch (err) {
      message.error(await errorDetail(err))
      throw err
    }
  }

  const handleReset = () => {
    modal.confirm({
      title: 'Reset seluruh database HRD?',
      content:
        'Semua data akan dihapus permanen. Hanya admin 0000003 Kenzie Mihardja dan akun loginnya yang dipertahankan.',
      okText: 'Reset database',
      okType: 'danger',
      cancelText: 'Batal',
      onOk: runReset,
    })
  }

  return (
    <div>
      <Typography.Title level={3}>State Manager</Typography.Title>
      <Typography.Paragraph type="secondary">
        Unduh snapshot CSV lengkap (karyawan, shift, absensi, gaji, permohonan cuti/lembur,
        dan data sementara lainnya), atau pulihkan server ke isi file yang pernah diunduh.
      </Typography.Paragraph>

      {unlocked ? (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Typography.Title level={5} style={{ margin: 0 }}>
                Unduh state
              </Typography.Title>
              <Typography.Text type="secondary">
                File berisi seluruh tabel HRD, termasuk permohonan yang masih menunggu
                persetujuan.
              </Typography.Text>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                loading={stateExport.isPending}
              >
                Unduh CSV
              </Button>
            </Space>
          </Card>

          <Card>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Typography.Title level={5} style={{ margin: 0 }}>
                Pulihkan dari CSV
              </Typography.Title>
              <Alert
                type="warning"
                showIcon
                message="Pemulihan mengganti seluruh data HRD dengan isi file, bukan menambahkan."
              />
              <Upload.Dragger {...uploadProps} disabled={stateImport.isPending}>
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">
                  Klik atau seret file CSV hasil unduhan State Manager
                </p>
              </Upload.Dragger>
              <Button
                danger
                type="primary"
                icon={<UploadOutlined />}
                onClick={handleRestore}
                disabled={!selectedFile}
                loading={stateImport.isPending}
              >
                Pulihkan state
              </Button>
              {result && !result.ok && <ImportResultPanel result={result} />}
            </Space>
          </Card>

          <Card>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Typography.Title level={5} style={{ margin: 0 }}>
                Reset database
              </Typography.Title>
              <Alert
                type="error"
                showIcon
                message="Tindakan ini menghapus seluruh data secara permanen."
                description="Hanya admin 0000003 Kenzie Mihardja dan akun loginnya yang akan dipertahankan."
              />
              <Button
                danger
                type="primary"
                icon={<DeleteOutlined />}
                onClick={handleReset}
                loading={stateReset.isPending}
              >
                Reset database
              </Button>
            </Space>
          </Card>
        </Space>
      ) : null}

      <Modal
        title={
          <Space>
            <DatabaseOutlined />
            <span>State Manager</span>
          </Space>
        }
        open={!unlocked}
        closable={false}
        maskClosable={false}
        keyboard={false}
        okText="Buka"
        cancelText="Batal"
        onOk={handleUnlock}
        onCancel={goHome}
      >
        <Typography.Paragraph>
          Modul ini dikunci. Masukkan kata sandi untuk unduh atau pulihkan state.
        </Typography.Paragraph>
        {unlockError ? (
          <Alert
            type="error"
            showIcon
            message={unlockError}
            style={{ marginBottom: 16 }}
          />
        ) : null}
        <Form form={passwordForm} layout="vertical" onFinish={handleUnlock}>
          <Form.Item
            name="password"
            label="Kata sandi"
            rules={[{ required: true, message: 'Masukkan kata sandi.' }]}
          >
            <Input.Password autoFocus autoComplete="current-password" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

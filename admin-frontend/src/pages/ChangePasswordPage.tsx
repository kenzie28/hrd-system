import { useState } from 'react'
import { Alert, Button, Card, Form, Input, Typography, App as AntApp } from 'antd'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

interface ChangePasswordForm {
  new_password: string
}

export default function ChangePasswordPage() {
  const { changePassword, isAuthenticated, mustChangePassword, loading } =
    useAuth()
  const navigate = useNavigate()
  const { message } = AntApp.useApp()
  const [submitting, setSubmitting] = useState(false)

  if (!loading && !isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const onFinish = async (values: ChangePasswordForm) => {
    setSubmitting(true)
    try {
      await changePassword(values.new_password)
      message.success('Kata sandi berhasil diperbarui.')
      navigate('/', { replace: true })
    } catch {
      message.error('Gagal memperbarui kata sandi.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="admin-centered">
      <Card style={{ width: 360 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>
          Ubah Kata Sandi
        </Typography.Title>
        {mustChangePassword && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message="Silakan ganti kata sandi bawaan Anda sebelum melanjutkan."
          />
        )}
        <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="new_password"
            label="Kata Sandi Baru"
            rules={[{ required: true, message: 'Masukkan kata sandi baru.' }]}
          >
            <Input.Password
              placeholder="Kata sandi baru"
              autoComplete="new-password"
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={submitting}>
            Simpan
          </Button>
        </Form>
      </Card>
    </div>
  )
}

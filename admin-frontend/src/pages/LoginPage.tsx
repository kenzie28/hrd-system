import { useState } from 'react'
import { App as AntApp, Button, Card, Form, Input, Typography } from 'antd'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

interface LoginForm {
  karyawan_id: string
  password: string
}

export default function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()
  const { message } = AntApp.useApp()
  const [submitting, setSubmitting] = useState(false)

  if (!loading && isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const onFinish = async (values: LoginForm) => {
    setSubmitting(true)
    try {
      await login(values.karyawan_id.trim(), values.password)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'ID karyawan atau kata sandi salah.'
      message.error(detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="admin-centered">
      <Card style={{ width: 360 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>
          HRD Admin
        </Typography.Title>
        <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="karyawan_id"
            label="ID Karyawan"
            rules={[{ required: true, message: 'Masukkan ID karyawan.' }]}
          >
            <Input placeholder="ID karyawan (7 digit)" autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Kata Sandi"
            rules={[{ required: true, message: 'Masukkan kata sandi.' }]}
          >
            <Input.Password
              placeholder="Kata sandi"
              autoComplete="current-password"
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={submitting}>
            Masuk
          </Button>
        </Form>
      </Card>
    </div>
  )
}

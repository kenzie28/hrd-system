import { useState } from 'react'
import { Alert, App as AntApp, Button, Card, Form, Input, Typography } from 'antd'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { parseLoginError } from '../auth/loginError'

interface LoginForm {
  karyawan_id: string
  password: string
}

export default function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<LoginForm>()
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  if (!loading && isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const onFinish = async (values: LoginForm) => {
    setSubmitting(true)
    setFormError(null)
    form.setFields([
      { name: 'karyawan_id', errors: [] },
      { name: 'password', errors: [] },
    ])
    try {
      await login(values.karyawan_id.trim(), values.password)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const { message: detail, field } = parseLoginError(err)
      setFormError(detail)
      if (field === 'karyawan_id' || field === 'password') {
        form.setFields([{ name: field, errors: [detail] }])
      }
      message.error(detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="admin-centered">
      <Card className="auth-card">
        <Typography.Title level={3} style={{ textAlign: 'center' }}>
          HRD Admin
        </Typography.Title>
        {formError ? (
          <Alert
            type="error"
            showIcon
            message={formError}
            style={{ marginBottom: 16 }}
          />
        ) : null}
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          requiredMark={false}
        >
          <Form.Item
            name="karyawan_id"
            label="ID Karyawan"
            rules={[{ required: true, message: 'Masukkan ID karyawan.' }]}
          >
            <Input
              placeholder="ID karyawan (7 digit)"
              autoComplete="username"
              maxLength={7}
            />
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

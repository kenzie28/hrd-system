import { HomeOutlined, LogoutOutlined } from '@ant-design/icons'
import { Button, Layout, Space, Typography } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function PortalLayout() {
  const { karyawan, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Space>
          {location.pathname !== '/' && (
            <Button
              type="text"
              icon={<HomeOutlined />}
              style={{ color: '#fff' }}
              onClick={() => navigate('/')}
            >
              Home
            </Button>
          )}
          <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
            Portal Karyawan
          </Typography.Title>
        </Space>
        <Space>
          {karyawan && (
            <Typography.Text style={{ color: '#fff' }}>
              {karyawan.nama} ({karyawan.karyawan_id})
            </Typography.Text>
          )}
          <Button
            type="text"
            icon={<LogoutOutlined />}
            style={{ color: '#fff' }}
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            Keluar
          </Button>
        </Space>
      </Layout.Header>
      <Layout.Content style={{ padding: 24 }}>
        <div
          style={{
            background: '#fff',
            borderRadius: 8,
            padding: 24,
            maxWidth: 960,
            margin: '0 auto',
          }}
        >
          <Outlet />
        </div>
      </Layout.Content>
    </Layout>
  )
}

import { HomeOutlined, LogoutOutlined } from '@ant-design/icons'
import { Button, Layout } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function PortalLayout() {
  const { karyawan, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const userLabel = karyawan
    ? `${karyawan.nama} (${karyawan.karyawan_id})`
    : ''

  return (
    <Layout className="app-shell">
      <Layout.Header className="app-header">
        <div className="app-header-left">
          {location.pathname !== '/' && (
            <Button
              type="text"
              icon={<HomeOutlined />}
              className="app-header-btn"
              aria-label="Home"
              onClick={() => navigate('/')}
            >
              <span className="app-header-btn-label">Home</span>
            </Button>
          )}
          <span className="app-header-title">
            <span className="app-header-title-full">Portal Karyawan</span>
            <span className="app-header-title-short">Portal</span>
          </span>
        </div>
        <div className="app-header-right">
          {karyawan && (
            <span className="app-header-user" title={userLabel}>
              <span className="app-header-user-name">{karyawan.nama}</span>
              <span className="app-header-user-id">
                {' '}
                ({karyawan.karyawan_id})
              </span>
            </span>
          )}
          <Button
            type="text"
            icon={<LogoutOutlined />}
            className="app-header-btn"
            aria-label="Keluar"
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            <span className="app-header-btn-label">Keluar</span>
          </Button>
        </div>
      </Layout.Header>
      <Layout.Content className="app-content">
        <div className="app-content-inner">
          <Outlet />
        </div>
      </Layout.Content>
    </Layout>
  )
}

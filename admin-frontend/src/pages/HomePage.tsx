import {
  CalendarOutlined,
  KeyOutlined,
  ScheduleOutlined,
  WalletOutlined,
} from '@ant-design/icons'
import { Card, Col, Row, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

interface ModuleCard {
  key: string
  title: string
  description: string
  icon: React.ReactNode
  path: string
}

const MODULES: ModuleCard[] = [
  {
    key: 'absensi',
    title: 'Absensi',
    description: 'Kelola shift, jadwal, absensi, dan rekap kehadiran.',
    icon: <ScheduleOutlined style={{ fontSize: 32 }} />,
    path: '/absensi',
  },
  {
    key: 'cuti',
    title: 'Cuti & Izin',
    description: 'Lihat cuti dan setujui permohonan.',
    icon: <CalendarOutlined style={{ fontSize: 32 }} />,
    path: '/cuti',
  },
  {
    key: 'reset-password',
    title: 'Reset Password Karyawan',
    description: 'Reset kata sandi portal karyawan ke default.',
    icon: <KeyOutlined style={{ fontSize: 32 }} />,
    path: '/reset-password',
  },
  {
    key: 'gaji',
    title: 'Gaji',
    description: 'Modul gaji (segera hadir).',
    icon: <WalletOutlined style={{ fontSize: 32 }} />,
    path: '/gaji',
  },
]

export default function HomePage() {
  const navigate = useNavigate()
  const { karyawan } = useAuth()

  return (
    <div>
      <Typography.Title level={3}>
        Selamat datang{karyawan ? `, ${karyawan.nama}` : ''}
      </Typography.Title>
      <Row gutter={[16, 16]}>
        {MODULES.map((module) => (
          <Col xs={24} sm={12} key={module.key}>
            <Card hoverable onClick={() => navigate(module.path)}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                {module.icon}
                <div>
                  <Typography.Title level={4} style={{ margin: 0 }}>
                    {module.title}
                  </Typography.Title>
                  <Typography.Text type="secondary">
                    {module.description}
                  </Typography.Text>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}

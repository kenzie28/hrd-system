import {
  CalendarOutlined,
  ClockCircleOutlined,
  SolutionOutlined,
  WalletOutlined,
} from '@ant-design/icons'
import { Card, Col, Row, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useCutiApprovals } from '../api/cuti'
import { useLemburApprovals } from '../api/lembur'
import { useAuth } from '../auth/AuthContext'
import { MIN_SUPERVISOR_LEVEL } from '../constants'

interface ModuleCard {
  key: string
  title: string
  description: string
  icon: React.ReactNode
  path: string
  pendingCount?: number
}

export default function HomePage() {
  const navigate = useNavigate()
  const { karyawan } = useAuth()
  const isSupervisor = (karyawan?.level ?? 0) >= MIN_SUPERVISOR_LEVEL
  const { data: cutiApprovals } = useCutiApprovals(isSupervisor)
  const { data: lemburApprovals } = useLemburApprovals(isSupervisor)

  const modules: ModuleCard[] = [
    {
      key: 'gaji',
      title: 'Gaji',
      description: 'Lihat rincian komponen gaji per bulan.',
      icon: <WalletOutlined className="home-module-icon" />,
      path: '/gaji',
    },
    {
      key: 'cuti',
      title: 'Cuti & Izin',
      description: isSupervisor
        ? 'Ajukan cuti, pantau status, dan setujui permohonan.'
        : 'Ajukan cuti dan pantau status.',
      icon: <CalendarOutlined className="home-module-icon" />,
      path: '/cuti',
      pendingCount: cutiApprovals?.length ?? 0,
    },
    {
      key: 'lembur',
      title: 'Lembur',
      description: isSupervisor
        ? 'Ajukan lembur, pantau status, dan setujui permohonan.'
        : 'Ajukan lembur dan pantau status.',
      icon: <ClockCircleOutlined className="home-module-icon" />,
      path: '/lembur',
      pendingCount: lemburApprovals?.length ?? 0,
    },
    {
      key: 'absensi',
      title: 'Absensi',
      description: 'Lihat riwayat absensi Anda per bulan.',
      icon: <SolutionOutlined className="home-module-icon" />,
      path: '/absensi',
    },
  ]

  return (
    <div>
      <Typography.Title level={3} className="home-welcome">
        Selamat datang{karyawan ? `, ${karyawan.nama}` : ''}
      </Typography.Title>
      <Row gutter={[12, 12]} className="home-modules">
        {modules.map((module) => (
          <Col xs={24} sm={12} key={module.key}>
            <Card
              hoverable
              className="home-module-card"
              onClick={() => navigate(module.path)}
            >
              <div className="home-module-body">
                {module.icon}
                <div className="home-module-text">
                  <div className="home-module-title-row">
                    <Typography.Title level={4}>{module.title}</Typography.Title>
                    {(module.pendingCount ?? 0) > 0 && (
                      <span
                        className="home-module-badge"
                        aria-label={`${module.pendingCount} menunggu persetujuan`}
                      >
                        {module.pendingCount! > 99 ? '99+' : module.pendingCount}
                      </span>
                    )}
                  </div>
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

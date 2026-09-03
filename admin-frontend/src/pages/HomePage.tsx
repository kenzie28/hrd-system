import {
  CalendarOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
  FlagOutlined,
  ScheduleOutlined,
  SolutionOutlined,
  TeamOutlined,
  WalletOutlined,
} from '@ant-design/icons'
import { Card, Col, Row, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAbsensiConflicts, usePendingCuti, usePendingLembur } from '../api/hooks'
import { useAuth } from '../auth/AuthContext'

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
  const { data: pendingCuti } = usePendingCuti()
  const { data: pendingLembur } = usePendingLembur()
  const { data: absensiConflicts } = useAbsensiConflicts()
  const pendingCutiCount = pendingCuti?.length ?? 0
  const pendingLemburCount = pendingLembur?.length ?? 0
  const absensiConflictCount = absensiConflicts?.length ?? 0

  const modules: ModuleCard[] = [
    {
      key: 'shift',
      title: 'Shift',
      description: 'Kelola jam shift per lokasi kerja.',
      icon: <ScheduleOutlined className="home-module-icon" />,
      path: '/shift',
    },
    {
      key: 'absensi',
      title: 'Absensi',
      description: 'Tinjau riwayat absensi karyawan dan selesaikan konflik.',
      icon: <SolutionOutlined className="home-module-icon" />,
      path: '/absensi',
      pendingCount: absensiConflictCount,
    },
    {
      key: 'cuti',
      title: 'Cuti & Izin',
      description: 'Lihat cuti dan setujui permohonan.',
      icon: <CalendarOutlined className="home-module-icon" />,
      path: '/cuti',
      pendingCount: pendingCutiCount,
    },
    {
      key: 'lembur',
      title: 'Lembur',
      description: 'Lihat lembur dan setujui permohonan.',
      icon: <ClockCircleOutlined className="home-module-icon" />,
      path: '/lembur',
      pendingCount: pendingLemburCount,
    },
    {
      key: 'liburan',
      title: 'Liburan',
      description: 'Kelola hari libur nasional dan perusahaan.',
      icon: <FlagOutlined className="home-module-icon" />,
      path: '/liburan',
    },
    {
      key: 'karyawan',
      title: 'Master Karyawan',
      description: 'Kelola data karyawan, import/update CSV, dan reset password.',
      icon: <TeamOutlined className="home-module-icon" />,
      path: '/karyawan',
    },
    {
      key: 'lokasi',
      title: 'Master Lokasi Kerja',
      description: 'Kelola lokasi kerja dan import CSV.',
      icon: <EnvironmentOutlined className="home-module-icon" />,
      path: '/lokasi',
    },
    {
      key: 'gaji',
      title: 'Gaji',
      description: 'Modul gaji (segera hadir).',
      icon: <WalletOutlined className="home-module-icon" />,
      path: '/gaji',
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

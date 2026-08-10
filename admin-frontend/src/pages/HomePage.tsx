import {
  CalendarOutlined,
  ClockCircleOutlined,
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
      icon: <ScheduleOutlined style={{ fontSize: 32 }} />,
      path: '/shift',
    },
    {
      key: 'absensi',
      title: 'Absensi',
      description: 'Tinjau riwayat absensi karyawan dan selesaikan konflik.',
      icon: <SolutionOutlined style={{ fontSize: 32 }} />,
      path: '/absensi',
      pendingCount: absensiConflictCount,
    },
    {
      key: 'cuti',
      title: 'Cuti & Izin',
      description: 'Lihat cuti dan setujui permohonan.',
      icon: <CalendarOutlined style={{ fontSize: 32 }} />,
      path: '/cuti',
      pendingCount: pendingCutiCount,
    },
    {
      key: 'lembur',
      title: 'Lembur',
      description: 'Lihat lembur dan setujui permohonan.',
      icon: <ClockCircleOutlined style={{ fontSize: 32 }} />,
      path: '/lembur',
      pendingCount: pendingLemburCount,
    },
    {
      key: 'liburan',
      title: 'Liburan',
      description: 'Kelola hari libur nasional dan perusahaan.',
      icon: <FlagOutlined style={{ fontSize: 32 }} />,
      path: '/liburan',
    },
    {
      key: 'karyawan',
      title: 'Master Karyawan',
      description: 'Kelola data karyawan, import CSV, dan reset password.',
      icon: <TeamOutlined style={{ fontSize: 32 }} />,
      path: '/karyawan',
    },
    {
      key: 'gaji',
      title: 'Gaji',
      description: 'Modul gaji (segera hadir).',
      icon: <WalletOutlined style={{ fontSize: 32 }} />,
      path: '/gaji',
    },
  ]

  return (
    <div>
      <Typography.Title level={3}>
        Selamat datang{karyawan ? `, ${karyawan.nama}` : ''}
      </Typography.Title>
      <Row gutter={[16, 16]} style={{ paddingTop: 8, paddingRight: 8 }}>
        {modules.map((module) => (
          <Col xs={24} sm={12} key={module.key}>
            <div style={{ position: 'relative' }}>
              {(module.pendingCount ?? 0) > 0 && (
                <span
                  aria-label={`${module.pendingCount} menunggu persetujuan`}
                  style={{
                    position: 'absolute',
                    top: -8,
                    right: -8,
                    zIndex: 2,
                    minWidth: 22,
                    height: 22,
                    padding: '0 6px',
                    borderRadius: 11,
                    background: '#ff4d4f',
                    color: '#fff',
                    fontSize: 12,
                    fontWeight: 700,
                    lineHeight: '18px',
                    textAlign: 'center',
                    border: '2px solid #fff',
                    boxShadow: '0 2px 8px rgba(255, 77, 79, 0.45)',
                    pointerEvents: 'none',
                    boxSizing: 'border-box',
                  }}
                >
                  {module.pendingCount! > 99 ? '99+' : module.pendingCount}
                </span>
              )}
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
            </div>
          </Col>
        ))}
      </Row>
    </div>
  )
}

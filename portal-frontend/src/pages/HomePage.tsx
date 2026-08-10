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
      icon: <WalletOutlined style={{ fontSize: 32 }} />,
      path: '/gaji',
    },
    {
      key: 'cuti',
      title: 'Cuti & Izin',
      description: isSupervisor
        ? 'Ajukan cuti, pantau status, dan setujui permohonan.'
        : 'Ajukan cuti dan pantau status.',
      icon: <CalendarOutlined style={{ fontSize: 32 }} />,
      path: '/cuti',
      pendingCount: cutiApprovals?.length ?? 0,
    },
    {
      key: 'lembur',
      title: 'Lembur',
      description: isSupervisor
        ? 'Ajukan lembur, pantau status, dan setujui permohonan.'
        : 'Ajukan lembur dan pantau status.',
      icon: <ClockCircleOutlined style={{ fontSize: 32 }} />,
      path: '/lembur',
      pendingCount: lemburApprovals?.length ?? 0,
    },
    {
      key: 'absensi',
      title: 'Absensi',
      description: 'Lihat riwayat absensi Anda per bulan.',
      icon: <SolutionOutlined style={{ fontSize: 32 }} />,
      path: '/absensi',
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

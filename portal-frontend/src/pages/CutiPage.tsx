import { Badge, Tabs, Typography } from 'antd'
import type { ReactNode } from 'react'
import { useCutiApprovals } from '../api/cuti'
import { useAuth } from '../auth/AuthContext'
import { MIN_SUPERVISOR_LEVEL } from '../constants'
import AjukanCutiTab from './cuti/AjukanCutiTab'
import PersetujuanCutiTab from './cuti/PersetujuanCutiTab'
import StatusCutiTab from './cuti/StatusCutiTab'

export default function CutiPage() {
  const { karyawan } = useAuth()
  const isSupervisor = (karyawan?.level ?? 0) >= MIN_SUPERVISOR_LEVEL
  const { data: approvals } = useCutiApprovals(isSupervisor)
  const hasPending = (approvals?.length ?? 0) > 0

  const items: { key: string; label: ReactNode; children: ReactNode }[] = [
    { key: 'ajukan', label: 'Ajukan', children: <AjukanCutiTab /> },
    { key: 'status', label: 'Status', children: <StatusCutiTab /> },
  ]

  if (isSupervisor) {
    items.push({
      key: 'persetujuan',
      label: (
        <Badge dot={hasPending} offset={[6, 0]}>
          Persetujuan
        </Badge>
      ),
      children: <PersetujuanCutiTab />,
    })
  }

  return (
    <div>
      <Typography.Title level={3}>Cuti & Izin</Typography.Title>
      <Tabs defaultActiveKey="ajukan" items={items} destroyOnHidden />
    </div>
  )
}

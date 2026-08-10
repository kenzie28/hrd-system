import { Badge, Tabs, Typography } from 'antd'
import type { ReactNode } from 'react'
import { useLemburApprovals } from '../api/lembur'
import { useAuth } from '../auth/AuthContext'
import { MIN_SUPERVISOR_LEVEL } from '../constants'
import AjukanLemburTab from './lembur/AjukanLemburTab'
import PersetujuanLemburTab from './lembur/PersetujuanLemburTab'
import StatusLemburTab from './lembur/StatusLemburTab'

export default function LemburPage() {
  const { karyawan } = useAuth()
  const isSupervisor = (karyawan?.level ?? 0) >= MIN_SUPERVISOR_LEVEL
  const { data: approvals } = useLemburApprovals(isSupervisor)
  const hasPending = (approvals?.length ?? 0) > 0

  const items: { key: string; label: ReactNode; children: ReactNode }[] = [
    { key: 'ajukan', label: 'Ajukan', children: <AjukanLemburTab /> },
    { key: 'status', label: 'Status', children: <StatusLemburTab /> },
  ]

  if (isSupervisor) {
    items.push({
      key: 'persetujuan',
      label: (
        <Badge dot={hasPending} offset={[6, 0]}>
          Persetujuan
        </Badge>
      ),
      children: <PersetujuanLemburTab />,
    })
  }

  return (
    <div>
      <Typography.Title level={3}>Lembur</Typography.Title>
      <Tabs defaultActiveKey="ajukan" items={items} destroyOnHidden />
    </div>
  )
}

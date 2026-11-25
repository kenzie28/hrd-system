import { Badge, Tabs, Typography } from 'antd'
import type { ReactNode } from 'react'
import { usePendingLembur } from '../api/hooks'
import { LemburTab } from '../tabs/LemburTab'
import { PersetujuanLemburTab } from '../tabs/PersetujuanLemburTab'

export default function LemburPage() {
  const { data: pending } = usePendingLembur()
  const hasPending = (pending?.length ?? 0) > 0

  const items: { key: string; label: ReactNode; children: ReactNode }[] = [
    { key: 'lembur', label: 'Lembur', children: <LemburTab /> },
    {
      key: 'persetujuan-lembur',
      label: (
        <Badge dot={hasPending} offset={[6, 0]}>
          Persetujuan Lembur
        </Badge>
      ),
      children: <PersetujuanLemburTab />,
    },
  ]

  return (
    <div>
      <Typography.Title level={3}>Lembur</Typography.Title>
      <Tabs defaultActiveKey="lembur" destroyOnHidden items={items} />
    </div>
  )
}

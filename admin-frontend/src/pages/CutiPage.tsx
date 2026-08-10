import { Badge, Tabs, Typography } from 'antd'
import type { ReactNode } from 'react'
import { usePendingCuti } from '../api/hooks'
import { CutiTab } from '../tabs/CutiTab'
import { PersetujuanCutiTab } from '../tabs/PersetujuanCutiTab'

export default function CutiPage() {
  const { data: pending } = usePendingCuti()
  const hasPending = (pending?.length ?? 0) > 0

  const items: { key: string; label: ReactNode; children: ReactNode }[] = [
    { key: 'cuti', label: 'Cuti & Izin', children: <CutiTab /> },
    {
      key: 'persetujuan-cuti',
      label: (
        <Badge dot={hasPending} offset={[6, 0]}>
          Persetujuan Cuti & Izin
        </Badge>
      ),
      children: <PersetujuanCutiTab />,
    },
  ]

  return (
    <div>
      <Typography.Title level={3}>Cuti & Izin</Typography.Title>
      <Tabs defaultActiveKey="cuti" destroyOnHidden items={items} />
    </div>
  )
}

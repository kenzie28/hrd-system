import { Badge, Tabs, Typography } from 'antd'
import type { ReactNode } from 'react'
import { useAbsensiConflicts } from '../api/hooks'
import { AbsensiKonflikTab } from '../tabs/AbsensiKonflikTab'
import { AbsensiTab } from '../tabs/AbsensiTab'
import { ImportAbsensiTab } from '../tabs/ImportAbsensiTab'

export default function AbsensiPage() {
  const { data: conflicts } = useAbsensiConflicts()
  const hasConflicts = (conflicts?.length ?? 0) > 0

  const items: { key: string; label: ReactNode; children: ReactNode }[] = [
    { key: 'absensi', label: 'Absensi', children: <AbsensiTab /> },
    {
      key: 'konflik',
      label: (
        <Badge dot={hasConflicts} offset={[6, 0]}>
          Konflik Absensi
        </Badge>
      ),
      children: <AbsensiKonflikTab />,
    },
    { key: 'import', label: 'Import CSV', children: <ImportAbsensiTab /> },
  ]

  return (
    <div>
      <Typography.Title level={3}>Absensi</Typography.Title>
      <Tabs defaultActiveKey="absensi" destroyOnHidden items={items} />
    </div>
  )
}

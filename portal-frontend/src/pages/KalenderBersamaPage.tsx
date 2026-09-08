import { Badge, Tabs, Typography } from 'antd'
import type { ReactNode } from 'react'
import { useNotifikasi } from '../api/kalenderBersama'
import KalendarTab from './kalender-bersama/KalendarTab'
import KelolaGroupTab from './kalender-bersama/KelolaGroupTab'
import NotifikasiTab from './kalender-bersama/NotifikasiTab'

export default function KalenderBersamaPage() {
  const { data: notifikasi } = useNotifikasi()
  const unread = notifikasi?.length ?? 0

  const items: { key: string; label: ReactNode; children: ReactNode }[] = [
    { key: 'kalendar', label: 'Kalendar', children: <KalendarTab /> },
    {
      key: 'notifikasi',
      label: (
        <Badge count={unread} overflowCount={99} size="small" offset={[8, 0]}>
          Notifikasi
        </Badge>
      ),
      children: <NotifikasiTab />,
    },
    { key: 'kelola', label: 'Kelola Group', children: <KelolaGroupTab /> },
  ]

  return (
    <div className="kalender-bersama-page">
      <Typography.Title level={3}>Kalender Bersama</Typography.Title>
      <Tabs defaultActiveKey="kalendar" items={items} destroyOnHidden />
    </div>
  )
}

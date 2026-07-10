import { Tabs, Typography } from 'antd'
import { useAuth } from '../auth/AuthContext'
import { MIN_SUPERVISOR_LEVEL } from '../constants'
import AjukanCutiTab from './cuti/AjukanCutiTab'
import PersetujuanCutiTab from './cuti/PersetujuanCutiTab'
import StatusCutiTab from './cuti/StatusCutiTab'

export default function CutiPage() {
  const { karyawan } = useAuth()
  const isSupervisor = (karyawan?.level ?? 0) >= MIN_SUPERVISOR_LEVEL

  const items = [
    { key: 'ajukan', label: 'Ajukan Cuti', children: <AjukanCutiTab /> },
    { key: 'status', label: 'Status Cuti', children: <StatusCutiTab /> },
  ]

  if (isSupervisor) {
    items.push({
      key: 'persetujuan',
      label: 'Persetujuan',
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

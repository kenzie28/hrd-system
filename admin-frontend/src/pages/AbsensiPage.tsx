import { Tabs, Typography } from 'antd'
import { AbsensiTab } from '../tabs/AbsensiTab'
import { JadwalTab } from '../tabs/JadwalTab'
import { RekapTab } from '../tabs/RekapTab'
import { ShiftTab } from '../tabs/ShiftTab'

export default function AbsensiPage() {
  return (
    <div>
      <Typography.Title level={3}>Absensi</Typography.Title>
      <Tabs
        defaultActiveKey="shift"
        destroyOnHidden
        items={[
          { key: 'shift', label: 'Shift', children: <ShiftTab /> },
          { key: 'jadwal', label: 'Jadwal', children: <JadwalTab /> },
          { key: 'absensi', label: 'Absensi', children: <AbsensiTab /> },
          { key: 'rekap', label: 'Rekap Kehadiran', children: <RekapTab /> },
        ]}
      />
    </div>
  )
}

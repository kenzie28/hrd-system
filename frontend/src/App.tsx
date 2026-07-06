import { Layout, Tabs, Typography } from 'antd'
import { ShiftTab } from './tabs/ShiftTab'
import { JadwalTab } from './tabs/JadwalTab'
import { AbsensiTab } from './tabs/AbsensiTab'
import { CutiTab } from './tabs/CutiTab'
import { RekapTab } from './tabs/RekapTab'

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Header style={{ display: 'flex', alignItems: 'center' }}>
        <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
          HRD System — Attendance
        </Typography.Title>
      </Layout.Header>
      <Layout.Content style={{ padding: 24 }}>
        <div style={{ background: '#fff', borderRadius: 8, padding: 24 }}>
          <Tabs
            defaultActiveKey="shift"
            destroyOnHidden
            items={[
              { key: 'shift', label: 'Shift', children: <ShiftTab /> },
              { key: 'jadwal', label: 'Jadwal', children: <JadwalTab /> },
              { key: 'absensi', label: 'Absensi', children: <AbsensiTab /> },
              { key: 'cuti', label: 'Cuti', children: <CutiTab /> },
              { key: 'rekap', label: 'Rekap Kehadiran', children: <RekapTab /> },
            ]}
          />
        </div>
      </Layout.Content>
    </Layout>
  )
}

import { Tabs, Typography } from 'antd'
import { CutiTab } from '../tabs/CutiTab'
import { PersetujuanCutiTab } from '../tabs/PersetujuanCutiTab'

export default function CutiPage() {
  return (
    <div>
      <Typography.Title level={3}>Cuti & Izin</Typography.Title>
      <Tabs
        defaultActiveKey="cuti"
        destroyOnHidden
        items={[
          { key: 'cuti', label: 'Cuti & Izin', children: <CutiTab /> },
          {
            key: 'persetujuan-cuti',
            label: 'Persetujuan Cuti & Izin',
            children: <PersetujuanCutiTab />,
          },
        ]}
      />
    </div>
  )
}

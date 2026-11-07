import { Tabs, Typography } from 'antd'
import { DataTunjanganObatTab } from '../tabs/DataTunjanganObatTab'
import { ImportTunjanganObatTab } from '../tabs/ImportTunjanganObatTab'

export default function TunjanganObatPage() {
  return (
    <div>
      <Typography.Title level={3}>Tunjangan Obat</Typography.Title>
      <Tabs
        defaultActiveKey="data"
        destroyOnHidden
        items={[
          {
            key: 'data',
            label: 'Data Tunjangan Obat',
            children: <DataTunjanganObatTab />,
          },
          {
            key: 'import',
            label: 'Import CSV',
            children: <ImportTunjanganObatTab />,
          },
        ]}
      />
    </div>
  )
}

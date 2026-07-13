import { Tabs, Typography } from 'antd'
import { DataGajiTab } from '../tabs/DataGajiTab'
import { ImportGajiTab } from '../tabs/ImportGajiTab'

export default function GajiPage() {
  return (
    <div>
      <Typography.Title level={3}>Gaji</Typography.Title>
      <Tabs
        defaultActiveKey="import"
        destroyOnHidden
        items={[
          { key: 'import', label: 'Import CSV', children: <ImportGajiTab /> },
          { key: 'data', label: 'Data Gaji', children: <DataGajiTab /> },
        ]}
      />
    </div>
  )
}

import { Tabs, Typography } from 'antd'
import { DataDinasTab } from '../tabs/DataDinasTab'
import { DinasTab } from '../tabs/DinasTab'
import { ImportDinasTab } from '../tabs/ImportCutiTab'

export default function DinasPage() {
  return (
    <div>
      <Typography.Title level={3}>Dinas</Typography.Title>
      <Tabs
        defaultActiveKey="data"
        destroyOnHidden
        items={[
          { key: 'data', label: 'Dinas', children: <DataDinasTab /> },
          { key: 'buat', label: 'Buat Dinas', children: <DinasTab /> },
          { key: 'import', label: 'Import CSV', children: <ImportDinasTab /> },
        ]}
      />
    </div>
  )
}

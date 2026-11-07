import { Tabs, Typography } from 'antd'
import { DataKoreksiTab } from '../tabs/DataKoreksiTab'
import { ImportKoreksiTab } from '../tabs/ImportKoreksiTab'

export default function KoreksiPage() {
  return (
    <div>
      <Typography.Title level={3}>Koreksi</Typography.Title>
      <Tabs
        defaultActiveKey="data"
        destroyOnHidden
        items={[
          { key: 'data', label: 'Data Koreksi', children: <DataKoreksiTab /> },
          { key: 'import', label: 'Import CSV', children: <ImportKoreksiTab /> },
        ]}
      />
    </div>
  )
}

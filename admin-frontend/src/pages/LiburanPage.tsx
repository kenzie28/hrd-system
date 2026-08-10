import { Tabs, Typography } from 'antd'
import { DataLiburanTab } from '../tabs/DataLiburanTab'
import { ImportLiburanTab } from '../tabs/ImportLiburanTab'

export default function LiburanPage() {
  return (
    <div>
      <Typography.Title level={3}>Liburan</Typography.Title>
      <Tabs
        defaultActiveKey="data"
        destroyOnHidden
        items={[
          { key: 'data', label: 'Data Liburan', children: <DataLiburanTab /> },
          { key: 'import', label: 'Import CSV', children: <ImportLiburanTab /> },
        ]}
      />
    </div>
  )
}

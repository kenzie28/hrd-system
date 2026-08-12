import { Tabs, Typography } from 'antd'
import { DataLokasiTab } from '../tabs/DataLokasiTab'
import { ImportLokasiTab } from '../tabs/ImportLokasiTab'

export default function LokasiPage() {
  return (
    <div>
      <Typography.Title level={3}>Master Lokasi Kerja</Typography.Title>
      <Tabs
        defaultActiveKey="data"
        destroyOnHidden
        items={[
          { key: 'data', label: 'Data Lokasi', children: <DataLokasiTab /> },
          { key: 'import', label: 'Import CSV', children: <ImportLokasiTab /> },
        ]}
      />
    </div>
  )
}

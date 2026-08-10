import { Tabs, Typography } from 'antd'
import { ImportShiftTab } from '../tabs/ImportShiftTab'
import { ShiftTab } from '../tabs/ShiftTab'

export default function ShiftPage() {
  return (
    <div>
      <Typography.Title level={3}>Shift</Typography.Title>
      <Tabs
        defaultActiveKey="kelola"
        destroyOnHidden
        items={[
          { key: 'kelola', label: 'Kelola Shift', children: <ShiftTab /> },
          { key: 'import', label: 'Import CSV', children: <ImportShiftTab /> },
        ]}
      />
    </div>
  )
}

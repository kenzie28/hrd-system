import { useState } from 'react'
import { Button, DatePicker, Space, Typography } from 'antd'
import dayjs from 'dayjs'

export function ProcessGajiTab() {
  const [month, setMonth] = useState(() => dayjs())

  return (
    <Space direction="vertical" size="middle">
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        Pilih bulan untuk memproses gaji karyawan.
      </Typography.Paragraph>
      <DatePicker
        picker="month"
        value={month}
        onChange={(value) => value && setMonth(value)}
        allowClear={false}
      />
      <Button type="primary">Proses Gaji</Button>
    </Space>
  )
}

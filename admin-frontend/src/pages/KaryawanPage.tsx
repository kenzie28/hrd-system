import { Tabs, Typography } from 'antd'
import { DataKaryawanTab } from '../tabs/DataKaryawanTab'
import { ImportKaryawanTab } from '../tabs/ImportKaryawanTab'
import { ResetPasswordKaryawanTab } from '../tabs/ResetPasswordKaryawanTab'
import { UpdateKaryawanTab } from '../tabs/UpdateKaryawanTab'
import { UpsertKaryawanTab } from '../tabs/UpsertKaryawanTab'

export default function KaryawanPage() {
  return (
    <div>
      <Typography.Title level={3}>Master Karyawan</Typography.Title>
      <Tabs
        defaultActiveKey="data"
        destroyOnHidden
        items={[
          { key: 'data', label: 'Data Karyawan', children: <DataKaryawanTab /> },
          {
            key: 'import',
            label: 'Tambah Karyawan (CSV)',
            children: <ImportKaryawanTab />,
          },
          {
            key: 'update',
            label: 'Update Karyawan (CSV)',
            children: <UpdateKaryawanTab />,
          },
          {
            key: 'import-upsert',
            label: 'Impor Data Karyawan (CSV)',
            children: <UpsertKaryawanTab />,
          },
          {
            key: 'reset-password',
            label: 'Reset Password',
            children: <ResetPasswordKaryawanTab />,
          },
        ]}
      />
    </div>
  )
}

import { Badge, Tabs, Typography } from 'antd'
import { useState, type ReactNode } from 'react'
import { useAbsensiConflicts } from '../api/hooks'
import { AbsensiKonflikTab } from '../tabs/AbsensiKonflikTab'
import { AbsensiTab } from '../tabs/AbsensiTab'
import { ImportAbsensiTab } from '../tabs/ImportAbsensiTab'
import { ImportCutiTab, ImportSakitTab } from '../tabs/ImportCutiTab'
import { RekapAbsensiTab } from '../tabs/RekapAbsensiTab'

export default function AbsensiPage() {
  const { data: conflicts } = useAbsensiConflicts()
  const hasConflicts = (conflicts?.length ?? 0) > 0
  const [activeTab, setActiveTab] = useState('absensi')
  const [absensiTarget, setAbsensiTarget] = useState<{
    karyawanId: string
    bulan: string
  }>()

  const items: { key: string; label: ReactNode; children: ReactNode }[] = [
    {
      key: 'absensi',
      label: 'Absensi',
      children: (
        <AbsensiTab
          initialKaryawanId={absensiTarget?.karyawanId}
          initialBulan={absensiTarget?.bulan}
        />
      ),
    },
    {
      key: 'konflik',
      label: (
        <Badge dot={hasConflicts} offset={[6, 0]}>
          Konflik Absensi
        </Badge>
      ),
      children: <AbsensiKonflikTab />,
    },
    {
      key: 'rekap',
      label: 'Rekap Absensi',
      children: (
        <RekapAbsensiTab
          onViewAbsensi={(karyawanId, bulan) => {
            setAbsensiTarget({ karyawanId, bulan })
            setActiveTab('absensi')
          }}
        />
      ),
    },
    { key: 'import-absensi', label: 'Import CSV Absensi', children: <ImportAbsensiTab /> },
    { key: 'import-cuti', label: 'Import CSV Cuti', children: <ImportCutiTab /> },
    { key: 'import-sakit', label: 'Import CSV Sakit', children: <ImportSakitTab /> },
  ]

  return (
    <div>
      <Typography.Title level={3}>Absensi</Typography.Title>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        destroyOnHidden
        items={items}
      />
    </div>
  )
}

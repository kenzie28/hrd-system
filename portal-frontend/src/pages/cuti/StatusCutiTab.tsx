import { App as AntApp, Button, Popconfirm, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCancelCuti, useMyCuti } from '../../api/cuti'
import type { CutiStatus, PermohonanCuti } from '../../api/types'
import { CUTI_STATUS_COLORS } from '../../constants'

const INSTANT_CANCELLABLE = new Set<CutiStatus>([
  'MENUNGGU_SUPERVISOR',
  'MENUNGGU_HRD',
])

const APPROVED_SECTION = new Set<CutiStatus>([
  'APPROVED',
  'MENUNGGU_PEMBATALAN_SUPERVISOR',
  'MENUNGGU_PEMBATALAN_HRD',
])

export default function StatusCutiTab() {
  const { data, isLoading } = useMyCuti()
  const { message } = AntApp.useApp()
  const cancelCuti = useCancelCuti()

  const onCancel = async (id: number, approved: boolean) => {
    try {
      await cancelCuti.mutateAsync(id)
      message.success(
        approved
          ? 'Permohonan pembatalan dikirim ke supervisor.'
          : 'Permohonan cuti dibatalkan.',
      )
    } catch {
      message.error('Gagal membatalkan permohonan.')
    }
  }

  const rows = data ?? []
  const permohonan = rows.filter((r) => !APPROVED_SECTION.has(r.status))
  const approved = rows.filter((r) => APPROVED_SECTION.has(r.status))

  const baseColumns: ColumnsType<PermohonanCuti> = [
    { title: 'Tipe', dataIndex: 'tipe_display' },
    { title: 'Mulai', dataIndex: 'tanggal_mulai' },
    { title: 'Selesai', dataIndex: 'tanggal_selesai' },
    { title: 'Hari', dataIndex: 'jumlah_hari', width: 70 },
    {
      title: 'Supervisor',
      dataIndex: 'supervisor_nama',
      render: (v: string | null) => v ?? '-',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (_, r) => (
        <Tag color={CUTI_STATUS_COLORS[r.status]}>{r.status_display}</Tag>
      ),
    },
  ]

  const permohonanColumns: ColumnsType<PermohonanCuti> = [
    ...baseColumns,
    {
      title: 'Aksi',
      width: 120,
      render: (_, r) =>
        INSTANT_CANCELLABLE.has(r.status) ? (
          <Popconfirm
            title="Batalkan permohonan ini?"
            okText="Ya"
            cancelText="Tidak"
            onConfirm={() => onCancel(r.id, false)}
          >
            <Button danger size="small" loading={cancelCuti.isPending}>
              Batalkan
            </Button>
          </Popconfirm>
        ) : (
          '-'
        ),
    },
  ]

  const approvedColumns: ColumnsType<PermohonanCuti> = [
    ...baseColumns,
    {
      title: 'Aksi',
      width: 130,
      render: (_, r) =>
        r.can_batal ? (
          <Popconfirm
            title="Ajukan pembatalan cuti ini? Supervisor dan HRD harus menyetujui."
            okText="Ya"
            cancelText="Tidak"
            onConfirm={() => onCancel(r.id, true)}
          >
            <Button danger size="small" loading={cancelCuti.isPending}>
              Batal Cuti
            </Button>
          </Popconfirm>
        ) : (
          '-'
        ),
    },
  ]

  return (
    <>
      <Table<PermohonanCuti>
        rowKey="id"
        loading={isLoading}
        dataSource={permohonan}
        pagination={{ pageSize: 10 }}
        scroll={{ x: true }}
        columns={permohonanColumns}
        locale={{ emptyText: 'Tidak ada permohonan.' }}
      />
      {approved.length > 0 && (
        <>
          <Typography.Title level={5} style={{ marginTop: 24 }}>
            Cuti Disetujui
          </Typography.Title>
          <Table<PermohonanCuti>
            rowKey="id"
            dataSource={approved}
            pagination={{ pageSize: 10 }}
            scroll={{ x: true }}
            columns={approvedColumns}
          />
        </>
      )}
    </>
  )
}

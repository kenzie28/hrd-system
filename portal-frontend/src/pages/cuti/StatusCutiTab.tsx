import { App as AntApp, Button, Popconfirm, Table, Tag } from 'antd'
import { useCancelCuti, useMyCuti } from '../../api/cuti'
import type { PermohonanCuti } from '../../api/types'
import { CUTI_STATUS_COLORS } from '../../constants'

const CANCELLABLE = new Set(['MENUNGGU_SUPERVISOR', 'MENUNGGU_HRD'])

export default function StatusCutiTab() {
  const { data, isLoading } = useMyCuti()
  const { message } = AntApp.useApp()
  const cancelCuti = useCancelCuti()

  const onCancel = async (id: number) => {
    try {
      await cancelCuti.mutateAsync(id)
      message.success('Permohonan cuti dibatalkan.')
    } catch {
      message.error('Gagal membatalkan permohonan.')
    }
  }

  return (
    <Table<PermohonanCuti>
      rowKey="id"
      loading={isLoading}
      dataSource={data ?? []}
      pagination={{ pageSize: 10 }}
      scroll={{ x: true }}
      columns={[
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
        {
          title: 'Aksi',
          width: 120,
          render: (_, r) =>
            CANCELLABLE.has(r.status) ? (
              <Popconfirm
                title="Batalkan permohonan ini?"
                okText="Ya"
                cancelText="Tidak"
                onConfirm={() => onCancel(r.id)}
              >
                <Button danger size="small" loading={cancelCuti.isPending}>
                  Batalkan
                </Button>
              </Popconfirm>
            ) : (
              '-'
            ),
        },
      ]}
    />
  )
}

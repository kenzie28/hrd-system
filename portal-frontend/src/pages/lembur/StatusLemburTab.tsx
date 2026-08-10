import { App as AntApp, Button, Popconfirm, Table, Tag } from 'antd'
import { useCancelLembur, useMyLembur } from '../../api/lembur'
import type { PermohonanLembur } from '../../api/types'
import { LEMBUR_STATUS_COLORS } from '../../constants'

const CANCELLABLE = new Set(['MENUNGGU_SUPERVISOR', 'MENUNGGU_HRD'])

export default function StatusLemburTab() {
  const { data, isLoading } = useMyLembur()
  const { message } = AntApp.useApp()
  const cancelLembur = useCancelLembur()

  const onCancel = async (id: number) => {
    try {
      await cancelLembur.mutateAsync(id)
      message.success('Permohonan lembur dibatalkan.')
    } catch {
      message.error('Gagal membatalkan permohonan.')
    }
  }

  return (
    <Table<PermohonanLembur>
      rowKey="id"
      loading={isLoading}
      dataSource={data ?? []}
      pagination={{ pageSize: 10 }}
      scroll={{ x: true }}
      columns={[
        { title: 'Tanggal', dataIndex: 'tanggal' },
        {
          title: 'Supervisor',
          dataIndex: 'supervisor_nama',
          render: (v: string | null) => v ?? '-',
        },
        {
          title: 'Alasan',
          dataIndex: 'alasan',
          render: (v: string) => v || '-',
        },
        {
          title: 'Status',
          dataIndex: 'status',
          render: (_, r) => (
            <Tag color={LEMBUR_STATUS_COLORS[r.status]}>{r.status_display}</Tag>
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
                <Button danger size="small" loading={cancelLembur.isPending}>
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

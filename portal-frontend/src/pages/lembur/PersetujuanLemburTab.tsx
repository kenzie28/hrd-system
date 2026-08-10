import { App as AntApp, Button, Popconfirm, Space, Table, Tag } from 'antd'
import {
  useApproveLembur,
  useLemburApprovals,
  useRejectLembur,
} from '../../api/lembur'
import type { PermohonanLembur } from '../../api/types'
import { LEMBUR_STATUS_COLORS } from '../../constants'

export default function PersetujuanLemburTab() {
  const { data, isLoading } = useLemburApprovals(true)
  const { message } = AntApp.useApp()
  const approve = useApproveLembur()
  const reject = useRejectLembur()

  const onApprove = async (id: number) => {
    try {
      await approve.mutateAsync(id)
      message.success('Permohonan diteruskan ke HRD.')
    } catch {
      message.error('Gagal menyetujui permohonan.')
    }
  }

  const onReject = async (id: number) => {
    try {
      await reject.mutateAsync(id)
      message.success('Permohonan ditolak.')
    } catch {
      message.error('Gagal menolak permohonan.')
    }
  }

  return (
    <Table<PermohonanLembur>
      rowKey="id"
      loading={isLoading}
      dataSource={data ?? []}
      pagination={{ pageSize: 10 }}
      scroll={{ x: true }}
      locale={{ emptyText: 'Tidak ada permohonan menunggu persetujuan.' }}
      columns={[
        { title: 'Karyawan', dataIndex: 'karyawan_nama' },
        { title: 'Tanggal', dataIndex: 'tanggal' },
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
          width: 180,
          render: (_, r) => (
            <Space>
              <Button
                type="primary"
                size="small"
                loading={approve.isPending}
                onClick={() => onApprove(r.id)}
              >
                Setujui
              </Button>
              <Popconfirm
                title="Tolak permohonan ini?"
                okText="Ya"
                cancelText="Tidak"
                onConfirm={() => onReject(r.id)}
              >
                <Button danger size="small" loading={reject.isPending}>
                  Tolak
                </Button>
              </Popconfirm>
            </Space>
          ),
        },
      ]}
    />
  )
}

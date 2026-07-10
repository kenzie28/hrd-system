import { App as AntApp, Button, Popconfirm, Space, Table, Tag } from 'antd'
import {
  useApproveCuti,
  useCutiApprovals,
  useRejectCuti,
} from '../../api/cuti'
import type { PermohonanCuti } from '../../api/types'
import { CUTI_STATUS_COLORS } from '../../constants'

export default function PersetujuanCutiTab() {
  const { data, isLoading } = useCutiApprovals(true)
  const { message } = AntApp.useApp()
  const approve = useApproveCuti()
  const reject = useRejectCuti()

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
    <Table<PermohonanCuti>
      rowKey="id"
      loading={isLoading}
      dataSource={data ?? []}
      pagination={{ pageSize: 10 }}
      scroll={{ x: true }}
      locale={{ emptyText: 'Tidak ada permohonan menunggu persetujuan.' }}
      columns={[
        { title: 'Karyawan', dataIndex: 'karyawan_nama' },
        { title: 'Tipe', dataIndex: 'tipe_display' },
        { title: 'Mulai', dataIndex: 'tanggal_mulai' },
        { title: 'Selesai', dataIndex: 'tanggal_selesai' },
        { title: 'Hari', dataIndex: 'jumlah_hari', width: 70 },
        {
          title: 'Alasan',
          dataIndex: 'alasan',
          render: (v: string) => v || '-',
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

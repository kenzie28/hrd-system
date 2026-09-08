import { App as AntApp, Button, Popconfirm, Space, Table, Tag } from 'antd'
import {
  useApproveCuti,
  useCutiApprovals,
  useRejectCuti,
} from '../../api/cuti'
import type { PermohonanCuti } from '../../api/types'
import { CUTI_STATUS_COLORS } from '../../constants'

function isPembatalan(row: PermohonanCuti) {
  return row.status === 'MENUNGGU_PEMBATALAN_SUPERVISOR'
}

export default function PersetujuanCutiTab() {
  const { data, isLoading } = useCutiApprovals(true)
  const { message } = AntApp.useApp()
  const approve = useApproveCuti()
  const reject = useRejectCuti()

  const onApprove = async (row: PermohonanCuti) => {
    try {
      await approve.mutateAsync(row.id)
      message.success(
        isPembatalan(row)
          ? 'Pembatalan diteruskan ke HRD.'
          : 'Permohonan diteruskan ke HRD.',
      )
    } catch {
      message.error('Gagal menyetujui permohonan.')
    }
  }

  const onReject = async (row: PermohonanCuti) => {
    try {
      await reject.mutateAsync(row.id)
      message.success(
        isPembatalan(row)
          ? 'Pembatalan ditolak. Cuti tetap berlaku.'
          : 'Permohonan ditolak.',
      )
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
          width: 220,
          render: (_, r) => {
            const pembatalan = isPembatalan(r)
            return (
              <Space>
                <Button
                  type="primary"
                  size="small"
                  loading={approve.isPending}
                  onClick={() => onApprove(r)}
                >
                  {pembatalan ? 'Setujui pembatalan' : 'Setujui'}
                </Button>
                <Popconfirm
                  title={
                    pembatalan
                      ? 'Tolak pembatalan? Cuti tetap berlaku.'
                      : 'Tolak permohonan ini?'
                  }
                  okText="Ya"
                  cancelText="Tidak"
                  onConfirm={() => onReject(r)}
                >
                  <Button danger size="small" loading={reject.isPending}>
                    {pembatalan ? 'Tolak pembatalan' : 'Tolak'}
                  </Button>
                </Popconfirm>
              </Space>
            )
          },
        },
      ]}
    />
  )
}

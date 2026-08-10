import { App as AntApp, Button, Popconfirm, Space, Table, Tag } from 'antd'
import { usePendingLembur, useLemburApprovalMutations } from '../api/hooks'
import type { PermohonanLembur } from '../api/types'

export function PersetujuanLemburTab() {
  const { data, isLoading } = usePendingLembur()
  const { approve, reject } = useLemburApprovalMutations()
  const { message } = AntApp.useApp()

  const onApprove = async (id: number) => {
    try {
      await approve.mutateAsync(id)
      message.success('Lembur disetujui.')
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
      locale={{ emptyText: 'Tidak ada permohonan menunggu persetujuan HRD.' }}
      columns={[
        { title: 'ID Karyawan', dataIndex: 'karyawan_kode', width: 110 },
        { title: 'Karyawan', dataIndex: 'karyawan_nama' },
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
          dataIndex: 'status_display',
          render: (v: string) => <Tag color="blue">{v}</Tag>,
        },
        {
          title: 'Aksi',
          width: 190,
          render: (_, r) => (
            <Space>
              <Popconfirm
                title="Setujui permohonan lembur ini?"
                okText="Ya"
                cancelText="Tidak"
                onConfirm={() => onApprove(r.id)}
              >
                <Button type="primary" size="small" loading={approve.isPending}>
                  Setujui
                </Button>
              </Popconfirm>
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

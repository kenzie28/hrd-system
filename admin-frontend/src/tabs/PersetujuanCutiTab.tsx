import { App as AntApp, Button, Popconfirm, Space, Table, Tag } from 'antd'
import { usePendingCuti, useCutiApprovalMutations } from '../api/hooks'
import type { PermohonanCuti } from '../api/types'

function isPembatalan(row: PermohonanCuti) {
  return row.status === 'MENUNGGU_PEMBATALAN_HRD'
}

export function PersetujuanCutiTab() {
  const { data, isLoading } = usePendingCuti()
  const { approve, reject } = useCutiApprovalMutations()
  const { message } = AntApp.useApp()

  const onApprove = async (row: PermohonanCuti) => {
    try {
      const res = await approve.mutateAsync(row.id)
      const payload = res.data as { hari_dibuat?: number; hari_dihapus?: number }
      if (isPembatalan(row)) {
        const removed = payload.hari_dihapus
        message.success(
          removed != null
            ? `Pembatalan disetujui (${removed} hari dihapus, jatah cuti dikembalikan).`
            : 'Pembatalan disetujui.',
        )
      } else {
        const created = payload.hari_dibuat
        message.success(
          created != null
            ? `Cuti disetujui (${created} hari dibuat).`
            : 'Cuti disetujui.',
        )
      }
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
      locale={{ emptyText: 'Tidak ada permohonan menunggu persetujuan HRD.' }}
      columns={[
        { title: 'ID Karyawan', dataIndex: 'karyawan_id', width: 110 },
        { title: 'Karyawan', dataIndex: 'karyawan_nama' },
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
          title: 'Alasan',
          dataIndex: 'alasan',
          render: (v: string) => v || '-',
        },
        {
          title: 'Status',
          dataIndex: 'status',
          render: (_, r) => (
            <Tag color={isPembatalan(r) ? 'orange' : 'blue'}>
              {r.status_display}
            </Tag>
          ),
        },
        {
          title: 'Aksi',
          width: 240,
          render: (_, r) => {
            const pembatalan = isPembatalan(r)
            return (
              <Space>
                <Popconfirm
                  title={
                    pembatalan
                      ? 'Setujui pembatalan dan kembalikan jatah cuti?'
                      : 'Setujui dan buat entri cuti?'
                  }
                  okText="Ya"
                  cancelText="Tidak"
                  onConfirm={() => onApprove(r)}
                >
                  <Button type="primary" size="small" loading={approve.isPending}>
                    {pembatalan ? 'Setujui pembatalan' : 'Setujui'}
                  </Button>
                </Popconfirm>
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

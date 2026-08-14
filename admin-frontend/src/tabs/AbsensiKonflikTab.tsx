import { App as AntApp, Button, Card, Empty, Popconfirm, Space, Table, Typography } from 'antd'
import { useAbsensiConflictMutations, useAbsensiConflicts } from '../api/hooks'
import type { Absensi } from '../api/types'
import { JamKeluar } from '../components/JamKeluar'
import { fmtTime } from '../constants'

export function AbsensiKonflikTab() {
  const { data, isLoading } = useAbsensiConflicts()
  const { resolve, remove } = useAbsensiConflictMutations()
  const { message } = AntApp.useApp()

  const onResolve = async (id: number) => {
    try {
      await resolve.mutateAsync(id)
      message.success('Konflik diselesaikan — entri lain untuk hari ini dihapus.')
    } catch {
      message.error('Gagal menyelesaikan konflik.')
    }
  }

  const onDelete = async (id: number) => {
    try {
      await remove.mutateAsync(id)
      message.success('Entri absensi dihapus.')
    } catch {
      message.error('Gagal menghapus entri.')
    }
  }

  if (!isLoading && (data?.length ?? 0) === 0) {
    return <Empty description="Tidak ada konflik absensi yang perlu diselesaikan." />
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {isLoading && <Typography.Text type="secondary">Memuat…</Typography.Text>}
      {(data ?? []).map((group) => (
        <Card
          key={`${group.karyawan_id}-${group.tanggal}`}
          size="small"
          title={`${group.karyawan_nama} — ${group.tanggal}`}
        >
          <Table<Absensi>
            rowKey="id"
            size="small"
            dataSource={group.entries}
            pagination={false}
            locale={{ emptyText: 'Tidak ada entri.' }}
            columns={[
              { title: 'Lokasi', dataIndex: 'lokasi_nama' },
              { title: 'Jam Masuk', dataIndex: 'jam_masuk', render: fmtTime },
              { title: 'Durasi', dataIndex: 'durasi', render: (d: string) => d.slice(0, 5) },
              {
                title: 'Jam Keluar',
                render: (_, entry) => (
                  <JamKeluar
                    jamKeluar={entry.jam_keluar}
                    keluarHariOffset={entry.keluar_hari_offset}
                  />
                ),
              },
              {
                title: 'Aksi',
                width: 220,
                render: (_, entry) => (
                  <Space>
                    <Popconfirm
                      title="Gunakan entri ini dan hapus entri lain untuk hari ini?"
                      okText="Ya"
                      cancelText="Tidak"
                      onConfirm={() => onResolve(entry.id)}
                    >
                      <Button type="primary" size="small" loading={resolve.isPending}>
                        Gunakan Ini
                      </Button>
                    </Popconfirm>
                    <Popconfirm
                      title="Hapus entri ini?"
                      okText="Ya"
                      cancelText="Tidak"
                      onConfirm={() => onDelete(entry.id)}
                    >
                      <Button danger size="small" loading={remove.isPending}>
                        Hapus
                      </Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      ))}
    </Space>
  )
}

import { App as AntApp, Avatar, Button, List } from 'antd'
import { useDismissNotifikasi, useNotifikasi } from '../../api/kalenderBersama'
import type { CutiNotifikasi } from '../../api/types'

function initials(nama: string) {
  return nama
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

export default function NotifikasiTab() {
  const { message } = AntApp.useApp()
  const { data, isLoading } = useNotifikasi()
  const dismiss = useDismissNotifikasi()

  const onDismiss = async (item: CutiNotifikasi) => {
    try {
      await dismiss.mutateAsync(item.id)
      message.success('Notifikasi ditutup.')
    } catch {
      message.error('Gagal menutup notifikasi.')
    }
  }

  return (
    <List
      loading={isLoading}
      itemLayout="horizontal"
      dataSource={data ?? []}
      locale={{ emptyText: 'Tidak ada notifikasi.' }}
      renderItem={(item) => (
        <List.Item
          actions={[
            <Button
              key="tutup"
              type="link"
              loading={dismiss.isPending}
              onClick={() => onDismiss(item)}
            >
              Tutup
            </Button>,
          ]}
        >
          <List.Item.Meta
            avatar={<Avatar>{initials(item.karyawan_nama)}</Avatar>}
            title={`${item.karyawan_nama} (${item.karyawan_id})`}
            description={`${item.tipe_display}, ${item.tanggal_mulai} s/d ${item.tanggal_selesai}`}
          />
        </List.Item>
      )}
    />
  )
}

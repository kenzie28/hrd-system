import {
  App as AntApp,
  Avatar,
  Button,
  Empty,
  Input,
  List,
  Popconfirm,
  Spin,
} from 'antd'
import { useEffect, useState } from 'react'
import {
  useKaryawanSearch,
  useLangganan,
  useSubscribe,
  useUnsubscribe,
} from '../../api/kalenderBersama'
import type { KaryawanSearchHit, Langganan } from '../../api/types'

function useDebouncedValue(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(id)
  }, [value, delay])
  return debounced
}

function initials(nama: string) {
  return nama
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function personSubtitle(jabatan: string, karyawanId: string) {
  return jabatan ? `${jabatan} · ${karyawanId}` : `ID ${karyawanId}`
}

export default function KelolaGroupTab() {
  const { message } = AntApp.useApp()
  const [query, setQuery] = useState('')
  const debounced = useDebouncedValue(query, 300)
  const { data: group, isLoading: groupLoading } = useLangganan()
  const { data: hits, isFetching: searching } = useKaryawanSearch(debounced)
  const subscribe = useSubscribe()
  const unsubscribe = useUnsubscribe()
  const showResults = debounced.trim().length >= 2

  const onAdd = async (hit: KaryawanSearchHit) => {
    try {
      await subscribe.mutateAsync(hit.karyawan_id)
      message.success('Rekan ditambahkan ke grup.')
      setQuery('')
    } catch {
      message.error('Gagal menambahkan rekan ke grup.')
    }
  }

  const onRemove = async (row: Langganan) => {
    try {
      await unsubscribe.mutateAsync(row.karyawan_id)
      message.success('Rekan dihapus dari grup.')
    } catch {
      message.error('Gagal menghapus rekan dari grup.')
    }
  }

  return (
    <div className="kb-group">
      <Input.Search
        allowClear
        size="large"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Cari nama atau ID karyawan"
        aria-label="Cari nama atau ID karyawan"
      />

      {showResults && (
        <div className="kb-group-results">
          <Spin spinning={searching}>
            {(hits?.length ?? 0) === 0 && !searching ? (
              <Empty description="Tidak ada hasil." />
            ) : (
              <List
                itemLayout="horizontal"
                dataSource={hits ?? []}
                renderItem={(hit) => (
                  <List.Item
                    actions={[
                      <Button
                        key="add"
                        type="primary"
                        disabled={hit.sudah_di_grup || subscribe.isPending}
                        onClick={() => onAdd(hit)}
                      >
                        {hit.sudah_di_grup ? 'Sudah di grup' : 'Tambah'}
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={<Avatar>{initials(hit.nama)}</Avatar>}
                      title={hit.nama}
                      description={personSubtitle(hit.jabatan, hit.karyawan_id)}
                    />
                  </List.Item>
                )}
              />
            )}
          </Spin>
        </div>
      )}

      <h4 className="kb-group-heading">Grup Anda</h4>
      <List
        loading={groupLoading}
        itemLayout="horizontal"
        dataSource={group ?? []}
        locale={{
          emptyText:
            'Belum ada rekan di grup. Cari nama atau ID untuk menambah.',
        }}
        renderItem={(row) => (
          <List.Item
            actions={[
              <Popconfirm
                key="cancel"
                title={`Hapus ${row.nama} dari grup?`}
                okText="Ya"
                cancelText="Tidak"
                onConfirm={() => onRemove(row)}
              >
                <Button danger loading={unsubscribe.isPending}>
                  Batalkan
                </Button>
              </Popconfirm>,
            ]}
          >
            <List.Item.Meta
              avatar={<Avatar>{initials(row.nama)}</Avatar>}
              title={row.nama}
              description={personSubtitle(row.jabatan, row.karyawan_id)}
            />
          </List.Item>
        )}
      />
    </div>
  )
}

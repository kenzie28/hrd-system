import { useState } from 'react'
import { App as AntApp, Alert, Input, Switch, Table, Typography } from 'antd'
import axios from 'axios'
import { useGajiKaryawan, useUpdateGajiKaryawan } from '../api/hooks'
import type { GajiKaryawan } from '../api/types'

function errorMessage(err: unknown) {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail) return detail
  }
  return 'Gagal menyimpan absensi dihitung.'
}

export function AbsensiDihitungTab() {
  const { data, isLoading, isError } = useGajiKaryawan()
  const update = useUpdateGajiKaryawan()
  const { message } = AntApp.useApp()
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [pending, setPending] = useState<{ id: string; value: boolean } | null>(null)

  if (isError) {
    return <Alert type="error" showIcon message="Gagal memuat daftar karyawan." />
  }

  const needle = query.trim().toLowerCase()
  const rows = (data ?? []).filter((row) => {
    if (!needle) return true
    return (
      row.karyawan_id.toLowerCase().includes(needle) ||
      row.nama.toLowerCase().includes(needle)
    )
  })

  const onToggle = async (karyawan_id: string, absensi_dihitung: boolean) => {
    setPending({ id: karyawan_id, value: absensi_dihitung })
    try {
      await update.mutateAsync({ karyawan_id, absensi_dihitung })
    } catch (err) {
      message.error(errorMessage(err))
    } finally {
      setPending(null)
    }
  }

  return (
    <div>
      <Typography.Paragraph type="secondary">
        Matikan untuk karyawan yang tidak dipotong alpa, berapa pun hari alpa mereka.
        Kehadiran tetap dicatat.
      </Typography.Paragraph>
      <Input.Search
        allowClear
        placeholder="Cari ID atau nama"
        style={{ maxWidth: 320, marginBottom: 16 }}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setPage(1)
        }}
      />
      <Table<GajiKaryawan>
        rowKey="karyawan_id"
        size="small"
        loading={isLoading}
        dataSource={rows}
        pagination={{
          current: page,
          pageSize: 20,
          showSizeChanger: false,
          onChange: setPage,
        }}
        scroll={{ x: true }}
        columns={[
          { title: 'ID Karyawan', dataIndex: 'karyawan_id', width: 140 },
          { title: 'Nama', dataIndex: 'nama' },
          {
            title: 'Absensi dihitung',
            dataIndex: 'absensi_dihitung',
            width: 180,
            render: (value: boolean, row) => (
              <Switch
                checked={pending?.id === row.karyawan_id ? pending.value : value}
                checkedChildren="Ya"
                unCheckedChildren="Tidak"
                loading={pending?.id === row.karyawan_id}
                disabled={pending != null && pending.id !== row.karyawan_id}
                onChange={(checked) => onToggle(row.karyawan_id, checked)}
              />
            ),
          },
        ]}
      />
    </div>
  )
}

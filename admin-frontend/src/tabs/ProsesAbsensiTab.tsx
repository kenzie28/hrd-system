import { useMemo, useState } from 'react'
import { App, Button, DatePicker, Empty, Space, Table, Typography } from 'antd'
import dayjs, { Dayjs } from 'dayjs'
import { useProsesAbsensi } from '../api/hooks'
import type { RekapAbsensi } from '../api/types'

interface IssueRow {
  key: string
  karyawan_nama: string
  tanggal: string | null
  pesan: string
}

export function ProsesAbsensiTab() {
  const { message } = App.useApp()
  const [month, setMonth] = useState<Dayjs>(() => dayjs())
  const [result, setResult] = useState<RekapAbsensi[] | null>(null)
  const proses = useProsesAbsensi()

  const issues = useMemo<IssueRow[]>(() => {
    if (!result) return []
    return result.flatMap((row) =>
      row.catatan.map((note) => ({
        key: `${row.id}-${note.id}`,
        karyawan_nama: row.karyawan_nama,
        tanggal: note.tanggal,
        pesan: note.pesan,
      })),
    )
  }, [result])

  const onProses = async () => {
    try {
      const data = await proses.mutateAsync(month.format('YYYY-MM'))
      setResult(data)
      message.success(`Absensi ${month.format('YYYY-MM')} diproses.`)
    } catch {
      message.error('Gagal memproses absensi.')
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <DatePicker
          picker="month"
          value={month}
          onChange={(value) => value && setMonth(value)}
          allowClear={false}
        />
        <Button type="primary" loading={proses.isPending} onClick={onProses}>
          Proses
        </Button>
      </Space>

      {result && (
        <>
          <Typography.Text>
            Diproses {result.length} karyawan untuk {month.format('YYYY-MM')}.{' '}
            {issues.length === 0
              ? 'Tidak ada catatan.'
              : `${issues.length} catatan.`}
          </Typography.Text>
          {issues.length === 0 ? (
            <Empty description="Tidak ada keterlambatan, alpa, atau catatan lain." />
          ) : (
            <Table<IssueRow>
              rowKey="key"
              size="small"
              dataSource={issues}
              pagination={{ pageSize: 20, showSizeChanger: false }}
              scroll={{ x: 'max-content' }}
              columns={[
                { title: 'Karyawan', dataIndex: 'karyawan_nama' },
                {
                  title: 'Tanggal',
                  dataIndex: 'tanggal',
                  width: 120,
                  render: (value: string | null) => value ?? '—',
                },
                { title: 'Pesan', dataIndex: 'pesan' },
              ]}
            />
          )}
        </>
      )}
    </Space>
  )
}

import { useState } from 'react'
import { App as AntApp, Button, Card, Empty, Form, Modal, Space, Table, TimePicker, Typography } from 'antd'
import dayjs, { Dayjs } from 'dayjs'
import { useAbsensiConflictMutations, useAbsensiConflicts } from '../api/hooks'
import type { Absensi } from '../api/types'
import { JamKeluar } from '../components/JamKeluar'
import { fmtTime } from '../constants'
import { durasiFromTimes } from '../utils/absensi'

interface ResolveFormValues {
  jam_masuk: Dayjs
  jam_keluar: Dayjs
}

export function AbsensiKonflikTab() {
  const { data, isLoading } = useAbsensiConflicts()
  const { resolve } = useAbsensiConflictMutations()
  const { message } = AntApp.useApp()
  const [selected, setSelected] = useState<Absensi | null>(null)
  const [form] = Form.useForm<ResolveFormValues>()

  const openResolve = (entry: Absensi) => {
    setSelected(entry)
    form.setFieldsValue({
      jam_masuk: dayjs(`2000-01-01T${entry.jam_masuk}`),
      jam_keluar: dayjs(`2000-01-01T${entry.jam_keluar}`),
    })
  }

  const onResolve = async () => {
    if (!selected) return
    const values = await form.validateFields()
    try {
      await resolve.mutateAsync({
        id: selected.id,
        jam_masuk: values.jam_masuk.format('HH:mm:00'),
        durasi: durasiFromTimes(values.jam_masuk, values.jam_keluar),
      })
      message.success('Konflik diselesaikan — entri lain untuk hari ini dihapus.')
      setSelected(null)
    } catch {
      message.error('Gagal menyelesaikan konflik.')
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
          title={`${group.karyawan_nama} (${group.karyawan_id}) — ${group.tanggal}`}
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
                width: 120,
                render: (_, entry) => (
                  <Button type="primary" size="small" onClick={() => openResolve(entry)}>
                    Gunakan Ini
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      ))}

      <Modal
        title={
          selected
            ? `Gunakan Absensi — ${selected.karyawan_nama} (${selected.karyawan_id}), ${selected.tanggal}`
            : 'Gunakan Absensi'
        }
        open={selected != null}
        onOk={onResolve}
        okText="Gunakan Ini"
        confirmLoading={resolve.isPending}
        onCancel={() => setSelected(null)}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="jam_masuk" label="Jam Masuk" rules={[{ required: true, message: 'Wajib diisi' }]}>
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="jam_keluar" label="Jam Keluar" rules={[{ required: true, message: 'Wajib diisi' }]}>
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Typography.Text type="secondary">
            Entri lain pada tanggal ini akan dihapus. Jam keluar yang sama atau lebih awal
            dari jam masuk dianggap hari berikutnya.
          </Typography.Text>
        </Form>
      </Modal>
    </Space>
  )
}

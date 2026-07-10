import { useState } from 'react'
import { App as AntApp, Button, Popconfirm, Select, Space, Typography } from 'antd'
import { useKaryawan, useResetPassword } from '../api/hooks'

export default function ResetPasswordPage() {
  const { message } = AntApp.useApp()
  const { data: karyawanList, isLoading } = useKaryawan()
  const resetPassword = useResetPassword()
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const selectedKaryawan = karyawanList?.find((k) => k.id === selectedId)

  const handleReset = async () => {
    if (selectedId === null) return
    try {
      await resetPassword.mutateAsync(selectedId)
      message.success('Kata sandi berhasil direset.')
      setSelectedId(null)
    } catch {
      message.error('Gagal mereset kata sandi.')
    }
  }

  return (
    <div>
      <Typography.Title level={3}>Reset Password Karyawan</Typography.Title>
      <Typography.Paragraph type="secondary">
        Reset kata sandi portal karyawan ke default (123). Karyawan wajib mengganti
        kata sandi saat login berikutnya.
      </Typography.Paragraph>
      <Space direction="vertical" size="middle" style={{ width: '100%', maxWidth: 480 }}>
        <Select
          showSearch
          placeholder="Pilih karyawan"
          loading={isLoading}
          value={selectedId}
          onChange={setSelectedId}
          optionFilterProp="label"
          style={{ width: '100%' }}
          options={karyawanList?.map((k) => ({
            value: k.id,
            label: `${k.nama} (${k.karyawan_id})`,
          }))}
        />
        <Popconfirm
          title="Reset kata sandi?"
          description={
            selectedKaryawan
              ? `Kata sandi ${selectedKaryawan.nama} akan direset ke 123. Karyawan harus mengganti kata sandi saat login berikutnya.`
              : undefined
          }
          onConfirm={handleReset}
          okText="Reset"
          cancelText="Batal"
          disabled={selectedId === null}
        >
          <Button
            type="primary"
            danger
            disabled={selectedId === null}
            loading={resetPassword.isPending}
          >
            Reset Password
          </Button>
        </Popconfirm>
      </Space>
    </div>
  )
}

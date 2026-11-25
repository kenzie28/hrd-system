import { useEffect, useState } from 'react'
import { WalletOutlined } from '@ant-design/icons'
import { Alert, Form, Input, Modal, Space, Tabs, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  GAJI_MODULE_PASSWORD,
  clearGajiPassword,
  storeGajiPassword,
} from '../gajiPassword'
import { AbsensiDihitungTab } from '../tabs/AbsensiDihitungTab'
import { GajiKaryawanTab } from '../tabs/GajiKaryawanTab'
import { ProcessGajiTab } from '../tabs/ProcessGajiTab'
import { ImportBaseGajiTab, ImportGajiBulananTab } from '../tabs/WageCsvImportTab'

export default function GajiPage() {
  const navigate = useNavigate()
  const [passwordForm] = Form.useForm<{ password: string }>()
  const [unlocked, setUnlocked] = useState(false)
  const [unlockError, setUnlockError] = useState<string | null>(null)

  useEffect(() => {
    if (!unlocked) {
      clearGajiPassword()
      passwordForm.resetFields()
    }
  }, [unlocked, passwordForm])

  const goHome = () => navigate('/', { replace: true })

  const handleUnlock = async () => {
    const values = await passwordForm.validateFields()
    if (values.password !== GAJI_MODULE_PASSWORD) {
      setUnlockError('Kata sandi salah.')
      return
    }
    storeGajiPassword(values.password)
    setUnlockError(null)
    setUnlocked(true)
  }

  return (
    <div>
      <Typography.Title level={3}>Gaji</Typography.Title>
      {unlocked ? (
        <Tabs
          defaultActiveKey="daftar"
          destroyOnHidden
          items={[
            { key: 'daftar', label: 'Daftar Karyawan', children: <GajiKaryawanTab /> },
            {
              key: 'absensi',
              label: 'Absensi Dihitung',
              children: <AbsensiDihitungTab />,
            },
            { key: 'process', label: 'Process Gaji', children: <ProcessGajiTab /> },
            {
              key: 'base',
              label: 'Import CSV Base Gaji',
              children: <ImportBaseGajiTab />,
            },
            {
              key: 'bulanan',
              label: 'Import CSV Gaji Bulanan',
              children: <ImportGajiBulananTab />,
            },
          ]}
        />
      ) : null}

      <Modal
        title={
          <Space>
            <WalletOutlined />
            <span>Gaji</span>
          </Space>
        }
        open={!unlocked}
        closable={false}
        maskClosable={false}
        keyboard={false}
        okText="Buka"
        cancelText="Batal"
        onOk={handleUnlock}
        onCancel={goHome}
      >
        <Typography.Paragraph>
          Modul ini dikunci. Masukkan kata sandi untuk membuka gaji.
        </Typography.Paragraph>
        {unlockError ? (
          <Alert type="error" showIcon message={unlockError} style={{ marginBottom: 16 }} />
        ) : null}
        <Form form={passwordForm} layout="vertical" onFinish={handleUnlock}>
          <Form.Item
            name="password"
            label="Kata sandi"
            rules={[{ required: true, message: 'Masukkan kata sandi.' }]}
          >
            <Input.Password autoFocus autoComplete="current-password" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

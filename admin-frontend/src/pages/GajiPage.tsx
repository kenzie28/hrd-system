import { useState } from 'react'
import { WalletOutlined } from '@ant-design/icons'
import { Alert, Form, Input, Modal, Space, Tabs, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { ProcessGajiTab } from '../tabs/ProcessGajiTab'
import { ImportBaseGajiTab, ImportGajiBulananTab } from '../tabs/WageCsvImportTab'

const MODULE_PASSWORD = 'bears'
const PASSWORD_STORAGE_KEY = 'hrd_gaji_password'

function readStoredPassword(): string {
  try {
    return sessionStorage.getItem(PASSWORD_STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

function storePassword(password: string) {
  try {
    sessionStorage.setItem(PASSWORD_STORAGE_KEY, password)
  } catch {
    /* ignore quota / private mode */
  }
}

export default function GajiPage() {
  const navigate = useNavigate()
  const [passwordForm] = Form.useForm<{ password: string }>()
  const [unlocked, setUnlocked] = useState(() => readStoredPassword() === MODULE_PASSWORD)
  const [unlockError, setUnlockError] = useState<string | null>(null)

  const handleUnlock = async () => {
    const values = await passwordForm.validateFields()
    if (values.password !== MODULE_PASSWORD) {
      setUnlockError('Kata sandi salah.')
      return
    }
    storePassword(values.password)
    setUnlockError(null)
    setUnlocked(true)
  }

  return (
    <div>
      <Typography.Title level={3}>Gaji</Typography.Title>
      {unlocked ? (
        <Tabs
          defaultActiveKey="process"
          destroyOnHidden
          items={[
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
        onCancel={() => navigate('/')}
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

import {
  App as AntApp,
  Button,
  DatePicker,
  Form,
  Input,
  Select,
  Spin,
} from 'antd'
import type { Dayjs } from 'dayjs'
import {
  useCreateLembur,
  useLemburSupervisorOptions,
} from '../../api/lembur'
import type { CreatePermohonanLemburPayload } from '../../api/types'

interface FormValues {
  tanggal: Dayjs
  supervisor: string
  alasan?: string
}

export default function AjukanLemburTab() {
  const [form] = Form.useForm<FormValues>()
  const { message } = AntApp.useApp()
  const { data: supervisors, isLoading } = useLemburSupervisorOptions()
  const createLembur = useCreateLembur()

  const onFinish = async (values: FormValues) => {
    const payload: CreatePermohonanLemburPayload = {
      alasan: values.alasan ?? '',
      supervisor: values.supervisor,
      tanggal: values.tanggal.format('YYYY-MM-DD'),
    }
    try {
      await createLembur.mutateAsync(payload)
      message.success('Permohonan lembur berhasil diajukan.')
      form.resetFields()
    } catch {
      message.error('Gagal mengajukan permohonan lembur.')
    }
  }

  if (isLoading) {
    return <Spin />
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={onFinish}
      requiredMark={false}
      style={{ maxWidth: 480 }}
    >
      <Form.Item
        name="tanggal"
        label="Tanggal"
        rules={[{ required: true, message: 'Pilih tanggal.' }]}
      >
        <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
      </Form.Item>
      <Form.Item
        name="supervisor"
        label="Supervisor Penyetuju"
        rules={[{ required: true, message: 'Pilih supervisor.' }]}
        extra={
          !supervisors?.length
            ? 'Tidak ada supervisor yang tersedia untuk level Anda.'
            : undefined
        }
      >
        <Select
          placeholder="Pilih supervisor"
          disabled={!supervisors?.length}
          options={(supervisors ?? []).map((s) => ({
            value: s.karyawan_id,
            label: `${s.nama} (Level ${s.level})`,
          }))}
        />
      </Form.Item>
      <Form.Item name="alasan" label="Alasan (opsional)">
        <Input.TextArea rows={3} placeholder="Alasan pengajuan" />
      </Form.Item>
      <Button
        type="primary"
        htmlType="submit"
        loading={createLembur.isPending}
        disabled={!supervisors?.length}
      >
        Ajukan
      </Button>
    </Form>
  )
}

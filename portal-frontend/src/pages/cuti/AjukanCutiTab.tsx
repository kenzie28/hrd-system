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
import { useCreateCuti, useSupervisorOptions } from '../../api/cuti'
import type { CreatePermohonanCutiPayload, CutiTipe } from '../../api/types'
import { CUTI_TIPE_OPTIONS } from '../../constants'

interface FormValues {
  tipe: CutiTipe
  rentang: [Dayjs, Dayjs]
  supervisor: number
  alasan?: string
}

export default function AjukanCutiTab() {
  const [form] = Form.useForm<FormValues>()
  const { message } = AntApp.useApp()
  const { data: supervisors, isLoading } = useSupervisorOptions()
  const createCuti = useCreateCuti()

  const onFinish = async (values: FormValues) => {
    const payload: CreatePermohonanCutiPayload = {
      tipe: values.tipe,
      alasan: values.alasan ?? '',
      supervisor: values.supervisor,
      tanggal_mulai: values.rentang[0].format('YYYY-MM-DD'),
      tanggal_selesai: values.rentang[1].format('YYYY-MM-DD'),
    }
    try {
      await createCuti.mutateAsync(payload)
      message.success('Permohonan cuti berhasil diajukan.')
      form.resetFields()
    } catch {
      message.error('Gagal mengajukan permohonan cuti.')
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
        name="tipe"
        label="Tipe Cuti"
        rules={[{ required: true, message: 'Pilih tipe cuti.' }]}
      >
        <Select placeholder="Pilih tipe cuti" options={CUTI_TIPE_OPTIONS} />
      </Form.Item>
      <Form.Item
        name="rentang"
        label="Tanggal Mulai - Selesai"
        rules={[{ required: true, message: 'Pilih rentang tanggal.' }]}
        extra="Pilih tanggal yang sama di awal dan akhir untuk request cuti satu hari."
      >
        <DatePicker.RangePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
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
            value: s.id,
            label: `${s.nama} (Level ${s.level})`,
          }))}
        />
      </Form.Item>
      <Form.Item name="alasan" label="Alasan (opsional)">
        <Input.TextArea rows={3} placeholder="Alasan pengajuan cuti" />
      </Form.Item>
      <Button
        type="primary"
        htmlType="submit"
        loading={createCuti.isPending}
        disabled={!supervisors?.length}
      >
        Ajukan Cuti
      </Button>
    </Form>
  )
}

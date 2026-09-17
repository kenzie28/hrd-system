import {
  App as AntApp,
  Alert,
  Button,
  DatePicker,
  Form,
  Input,
  Select,
  Spin,
} from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useMemo } from 'react'
import { useCreateCuti, useSupervisorOptions } from '../../api/cuti'
import type { CreatePermohonanCutiPayload, CutiTipe } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import {
  CUTI_TAHUNAN_ADVANCE_NOTICE_DAYS,
  CUTI_TAHUNAN_ADVANCE_NOTICE_MIN_DAYS,
  CUTI_TIPE_OPTIONS,
  MAX_CONSECUTIVE_CUTI_TAHUNAN_DAYS,
} from '../../constants'

interface FormValues {
  tipe: CutiTipe
  rentang: [Dayjs, Dayjs]
  supervisor: string
  alasan?: string
}

export default function AjukanCutiTab() {
  const [form] = Form.useForm<FormValues>()
  const { message } = AntApp.useApp()
  const { karyawan } = useAuth()
  const { data: supervisors, isLoading } = useSupervisorOptions()
  const createCuti = useCreateCuti()

  const sisaCutiTahunan = karyawan?.cuti_tahunan ?? 0
  const tipe = Form.useWatch('tipe', form)

  const tipeOptions = useMemo(
    () =>
      CUTI_TIPE_OPTIONS.map((opt) =>
        opt.value === 'CUTI_TAHUNAN'
          ? {
              ...opt,
              label: `${opt.label} (Sisa: ${sisaCutiTahunan} hari)`,
              disabled: sisaCutiTahunan <= 0,
            }
          : opt,
      ),
    [sisaCutiTahunan],
  )

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
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={`Sisa jatah Cuti Tahunan Anda: ${sisaCutiTahunan} hari`}
      />
      <Form.Item
        name="tipe"
        label="Tipe"
        rules={[{ required: true, message: 'Pilih tipe.' }]}
      >
        <Select placeholder="Pilih tipe" options={tipeOptions} />
      </Form.Item>
      <Form.Item
        name="rentang"
        label="Tanggal Mulai - Selesai"
        dependencies={['tipe']}
        rules={[
          { required: true, message: 'Pilih rentang tanggal.' },
          {
            validator: (_, value?: [Dayjs, Dayjs]) => {
              if (!value || tipe !== 'CUTI_TAHUNAN') return Promise.resolve()
              const jumlahHari = value[1].diff(value[0], 'day') + 1
              if (jumlahHari > MAX_CONSECUTIVE_CUTI_TAHUNAN_DAYS) {
                return Promise.reject(
                  new Error(
                    `Cuti tahunan maksimal ${MAX_CONSECUTIVE_CUTI_TAHUNAN_DAYS} hari berturut-turut.`,
                  ),
                )
              }
              if (jumlahHari >= CUTI_TAHUNAN_ADVANCE_NOTICE_MIN_DAYS) {
                const earliest = dayjs()
                  .startOf('day')
                  .add(CUTI_TAHUNAN_ADVANCE_NOTICE_DAYS, 'day')
                if (value[0].startOf('day').isBefore(earliest, 'day')) {
                  return Promise.reject(
                    new Error(
                      `Pengajuan cuti tahunan 4 atau 5 hari harus dilakukan minimal ${CUTI_TAHUNAN_ADVANCE_NOTICE_DAYS} hari sebelumnya.`,
                    ),
                  )
                }
              }
              if (jumlahHari > sisaCutiTahunan) {
                return Promise.reject(
                  new Error(
                    `Sisa cuti tahunan Anda hanya ${sisaCutiTahunan} hari, tidak mencukupi untuk ${jumlahHari} hari yang diajukan.`,
                  ),
                )
              }
              return Promise.resolve()
            },
          },
        ]}
        extra={
          tipe === 'CUTI_TAHUNAN'
            ? `Cuti Tahunan maksimal ${MAX_CONSECUTIVE_CUTI_TAHUNAN_DAYS} hari berturut-turut. Pengajuan 4 atau 5 hari harus diajukan minimal ${CUTI_TAHUNAN_ADVANCE_NOTICE_DAYS} hari sebelumnya.`
            : 'Pilih tanggal yang sama di awal dan akhir untuk request cuti satu hari.'
        }
      >
        <DatePicker.RangePicker
          style={{ width: '100%' }}
          format="YYYY-MM-DD"
          disabledDate={(current, info) => {
            if (tipe !== 'CUTI_TAHUNAN' || !info?.from) return false
            const maxOffset = MAX_CONSECUTIVE_CUTI_TAHUNAN_DAYS - 1
            return (
              current.isBefore(info.from.subtract(maxOffset, 'day'), 'day') ||
              current.isAfter(info.from.add(maxOffset, 'day'), 'day')
            )
          }}
        />
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
        loading={createCuti.isPending}
        disabled={!supervisors?.length}
      >
        Ajukan
      </Button>
    </Form>
  )
}

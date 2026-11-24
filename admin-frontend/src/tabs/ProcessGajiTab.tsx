import { useEffect, useState } from 'react'
import { Alert, Button, DatePicker, Progress, Space, Typography, message } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import dayjs from 'dayjs'
import { useGajiExport, useGajiMonthReady, useProsesGaji, useProsesGajiJob } from '../api/hooks'
import type { ProsesGajiJob } from '../api/types'

function jobPercent(job: ProsesGajiJob): number {
  if (job.status === 'succeeded') return 100
  if (job.total <= 0) return 0
  return Math.min(100, Math.round((job.processed / job.total) * 100))
}

function startError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail) return detail
  }
  return 'Gagal memulai proses gaji.'
}

function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function ProcessGajiTab() {
  const queryClient = useQueryClient()
  const [month, setMonth] = useState(() => dayjs())
  const [jobId, setJobId] = useState<number | null>(null)
  const start = useProsesGaji()
  const download = useGajiExport()
  const jobQuery = useProsesGajiJob(jobId)
  const job = jobQuery.data
  const bulan = month.format('YYYY-MM')
  const ready = useGajiMonthReady(bulan)
  const jobActive = job?.status === 'pending' || job?.status === 'running'
  const busy = start.isPending || (jobActive && job?.bulan === bulan)
  const finishedThisMonth = job?.status === 'succeeded' && job.bulan === bulan
  const canDownload = !busy && (finishedThisMonth || (ready.data?.count ?? 0) > 0)

  useEffect(() => {
    if (finishedThisMonth) {
      queryClient.invalidateQueries({ queryKey: ['gaji-ready', bulan] })
    }
  }, [finishedThisMonth, bulan, queryClient])

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%', maxWidth: 480 }}>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        Pilih bulan untuk memproses gaji karyawan.
      </Typography.Paragraph>
      <DatePicker
        picker="month"
        value={month}
        onChange={(value) => value && setMonth(value)}
        allowClear={false}
      />
      <Space>
        <Button
          type="primary"
          loading={busy}
          onClick={() => {
            start.mutate(bulan, {
              onSuccess: (created) => setJobId(created.id),
            })
          }}
        >
          Proses Gaji
        </Button>
        {canDownload ? (
          <Button
            loading={download.isPending}
            onClick={() => {
              download.mutate(bulan, {
                onSuccess: ({ blob, filename }) => {
                  saveDownload(blob, filename)
                  message.success('CSV gaji berhasil diunduh.')
                },
                onError: (err) => {
                  message.error(err instanceof Error ? err.message : 'Gagal mengunduh gaji.')
                },
              })
            }}
          >
            Unduh CSV
          </Button>
        ) : null}
      </Space>
      {start.isError ? <Alert type="error" showIcon message={startError(start.error)} /> : null}
      {jobQuery.isError ? (
        <Alert type="error" showIcon message="Gagal membaca progres proses gaji." />
      ) : null}
      {job ? (
        <>
          <Progress
            percent={jobPercent(job)}
            status={
              job.status === 'failed'
                ? 'exception'
                : job.status === 'succeeded'
                  ? 'success'
                  : 'active'
            }
          />
          <Typography.Text>
            {job.processed} / {job.total} karyawan
          </Typography.Text>
          {job.status === 'succeeded' ? (
            <Alert type="success" showIcon message={job.message} />
          ) : null}
          {job.status === 'failed' ? (
            <Alert type="error" showIcon message={job.message || 'Proses gaji gagal.'} />
          ) : null}
        </>
      ) : null}
    </Space>
  )
}

import { Calendar, ConfigProvider, Spin, Tooltip, Typography } from 'antd'
import idID from 'antd/locale/id_ID'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import 'dayjs/locale/id'
import { useMemo } from 'react'
import { useKalender } from '../../api/kalenderBersama'
import type { KalenderHari } from '../../api/types'

function monthBounds() {
  const current = dayjs().startOf('month')
  const next = current.add(1, 'month')
  return {
    current,
    next,
    dari: current.format('YYYY-MM-DD'),
    sampai: next.endOf('month').format('YYYY-MM-DD'),
  }
}

function tooltipTitle(items: KalenderHari[]) {
  return (
    <div>
      {items.map((item) => (
        <div key={item.id}>
          {item.karyawan_nama} — {item.tipe_display}
          <div className="kb-cal-tooltip-range">
            {item.tanggal_mulai} s/d {item.tanggal_selesai}
          </div>
        </div>
      ))}
    </div>
  )
}

function MonthCalendar({
  month,
  byDate,
}: {
  month: Dayjs
  byDate: Map<string, KalenderHari[]>
}) {
  return (
    <div className="kb-cal-month">
      <Calendar
        fullscreen={false}
        value={month}
        headerRender={() => (
          <Typography.Title level={5} className="kb-cal-title">
            {month.locale('id').format('MMMM YYYY')}
          </Typography.Title>
        )}
        cellRender={(current, info) => {
          if (info.type !== 'date') return info.originNode
          if (!current.isSame(month, 'month')) {
            return null
          }
          const items = byDate.get(current.format('YYYY-MM-DD')) ?? []
          const body = (
            <div className="kb-cal-cell">
              {items.slice(0, 3).map((item) => (
                <div key={item.id} className="kb-cal-chip">
                  {item.karyawan_nama}
                </div>
              ))}
              {items.length > 3 && (
                <div className="kb-cal-more">+{items.length - 3}</div>
              )}
            </div>
          )
          if (!items.length) return body
          return (
            <Tooltip title={tooltipTitle(items)} placement="top">
              {body}
            </Tooltip>
          )
        }}
      />
    </div>
  )
}

export default function KalendarTab() {
  const { current, next, dari, sampai } = useMemo(() => monthBounds(), [])
  const { data, isLoading } = useKalender(dari, sampai)

  const byDate = useMemo(() => {
    const map = new Map<string, KalenderHari[]>()
    for (const row of data ?? []) {
      map.set(row.tanggal, [...(map.get(row.tanggal) ?? []), row])
    }
    return map
  }, [data])

  return (
    <ConfigProvider locale={idID}>
      <Spin spinning={isLoading}>
        <div className="kb-calendars">
          <MonthCalendar month={current} byDate={byDate} />
          <MonthCalendar month={next} byDate={byDate} />
        </div>
      </Spin>
    </ConfigProvider>
  )
}

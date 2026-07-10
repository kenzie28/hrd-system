import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Calendar,
  DatePicker,
  Segmented,
  Select,
  Space,
  Table,
} from 'antd'
import type { TableProps } from 'antd'
import dayjs, { Dayjs } from 'dayjs'
import { useKaryawan } from '../api/hooks'

export type ViewMode = 'table' | 'calendar'

export interface ViewModeToggleProps<T> {
  data: T[]
  loading?: boolean
  columns: TableProps<T>['columns']
  getDate: (record: T) => string
  /** Compact one-line rendering used inside calendar cells. */
  renderBadge: (record: T) => ReactNode
  karyawanId?: number
  onKaryawanChange: (id?: number) => void
  month: Dayjs
  onMonthChange: (month: Dayjs) => void
  /** Extra toolbar content, e.g. action buttons. */
  toolbarExtra?: ReactNode
}

export function ViewModeToggle<T extends { id: number }>({
  data,
  loading,
  columns,
  getDate,
  renderBadge,
  karyawanId,
  onKaryawanChange,
  month,
  onMonthChange,
  toolbarExtra,
}: ViewModeToggleProps<T>) {
  const [mode, setMode] = useState<ViewMode>('table')
  const { data: karyawan } = useKaryawan()

  const karyawanOptions = useMemo(
    () => (karyawan ?? []).map((k) => ({ label: k.nama, value: k.id })),
    [karyawan],
  )

  const byDate = useMemo(() => {
    const map = new Map<string, T[]>()
    for (const record of data) {
      const key = getDate(record)
      map.set(key, [...(map.get(key) ?? []), record])
    }
    return map
  }, [data, getDate])

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Segmented
          value={mode}
          onChange={(value) => setMode(value as ViewMode)}
          options={[
            { label: 'Table', value: 'table' },
            { label: 'Calendar', value: 'calendar' },
          ]}
        />
        <Select
          placeholder="Semua karyawan"
          style={{ minWidth: 180 }}
          allowClear
          options={karyawanOptions}
          value={karyawanId}
          onChange={(value) => onKaryawanChange(value ?? undefined)}
          showSearch
          optionFilterProp="label"
        />
        <DatePicker
          picker="month"
          value={month}
          onChange={(value) => value && onMonthChange(value)}
          allowClear={false}
        />
        {toolbarExtra}
      </Space>

      {mode === 'table' && (
        <Table<T>
          rowKey="id"
          size="small"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: false }}
        />
      )}

      {mode === 'calendar' && (
        <Calendar
          value={month}
          onPanelChange={(value) => onMonthChange(value)}
          onChange={(value) => {
            if (!value.isSame(month, 'month')) onMonthChange(value)
          }}
          cellRender={(current, info) => {
            if (info.type !== 'date') return info.originNode
            const items = byDate.get(dayjs(current).format('YYYY-MM-DD')) ?? []
            return (
              <ul className="calendar-cell-items">
                {items.map((record) => (
                  <li key={record.id}>{renderBadge(record)}</li>
                ))}
              </ul>
            )
          }}
        />
      )}
    </Space>
  )
}

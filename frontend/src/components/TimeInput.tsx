import { TimePicker } from 'antd'
import type { TimePickerProps } from 'antd'

const MASKED_TIME_FORMAT = { format: 'HH:mm', type: 'mask' as const }

const TIME_INPUT_DEFAULTS = {
  format: MASKED_TIME_FORMAT,
  minuteStep: 5,
  changeOnScroll: true,
  needConfirm: false,
  inputReadOnly: false,
  placeholder: 'HH:mm',
  showNow: false,
  showSecond: false,
  getPopupContainer: () => document.body,
} satisfies TimePickerProps

export function TimeInput({ style, ...props }: TimePickerProps) {
  return (
    <TimePicker
      {...TIME_INPUT_DEFAULTS}
      {...props}
      style={{ width: '100%', ...style }}
    />
  )
}

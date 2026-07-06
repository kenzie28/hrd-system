import { fmtTime } from '../constants'

interface JamKeluarProps {
  jamKeluar?: string | null
  keluarHariOffset?: number
}

export function JamKeluar({ jamKeluar, keluarHariOffset = 0 }: JamKeluarProps) {
  if (!jamKeluar) return <>-</>
  return (
    <>
      {fmtTime(jamKeluar)}
      {keluarHariOffset > 0 && <sup>+{keluarHariOffset}</sup>}
    </>
  )
}

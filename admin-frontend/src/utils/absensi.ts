import dayjs, { Dayjs } from 'dayjs'

export function parseDurasi(durasi: string): { jam: number; menit: number } {
  // DRF renders durations as "HH:MM:SS" (or "D HH:MM:SS" past 24h)
  const [dayPart, timePart] = durasi.includes(' ') ? durasi.split(' ') : ['0', durasi]
  const [h, m] = timePart.split(':').map(Number)
  return { jam: Number(dayPart) * 24 + h, menit: m }
}

export function getKeluarHariOffset(
  tanggal: string,
  jamMasuk: string | Dayjs,
  durasiJam: number,
  durasiMenit: number,
): number {
  const masuk =
    typeof jamMasuk === 'string'
      ? dayjs(`${tanggal}T${jamMasuk.slice(0, 8)}`)
      : dayjs(`${tanggal}T${jamMasuk.format('HH:mm:ss')}`)
  const keluar = masuk.add(durasiJam, 'hour').add(durasiMenit, 'minute')
  return keluar.startOf('day').diff(masuk.startOf('day'), 'day')
}

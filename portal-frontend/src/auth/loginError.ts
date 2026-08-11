import axios from 'axios'

export type LoginField = 'karyawan_id' | 'password'

export interface ParsedLoginError {
  message: string
  field?: LoginField
}

function asText(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map(asText).filter(Boolean).join(' ')
  }
  if (typeof value === 'object') {
    const parts = Object.values(value as Record<string, unknown>).map(asText)
    return parts.filter(Boolean).join(' ')
  }
  return String(value)
}

function normalizeField(value: unknown): LoginField | undefined {
  if (value === 'karyawan_id' || value === 'password') return value
  return undefined
}

function inferFieldFromMessage(message: string): LoginField | undefined {
  const lower = message.toLowerCase()
  if (lower.includes('tidak ditemukan') || lower.includes('belum terdaftar')) {
    return 'karyawan_id'
  }
  if (
    lower.includes('kata sandi') ||
    lower.includes('password') ||
    lower.includes('sandi salah')
  ) {
    return 'password'
  }
  return undefined
}

export function parseLoginError(err: unknown): ParsedLoginError {
  if (!axios.isAxiosError(err)) {
    return { message: 'Login gagal. Coba lagi.' }
  }

  const attempted =
    (typeof err.config?.baseURL === 'string' ? err.config.baseURL : '') +
    (typeof err.config?.url === 'string' ? err.config.url : '')

  if (!err.response) {
    return {
      message:
        `Tidak dapat terhubung ke server` +
        (attempted ? ` (${attempted})` : '') +
        '. Buka portal melalui port frontend, pastikan nginx mem-proxy /api, lalu rebuild: ./build.sh && ./deploy.sh.',
    }
  }

  const data = err.response.data
  let message = ''
  let field: LoginField | undefined

  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const body = data as Record<string, unknown>
    field = normalizeField(body.field)

    if (body.code === 'invalid_username' || body.code === 'missing_username') {
      field = 'karyawan_id'
    } else if (body.code === 'invalid_password') {
      field = 'password'
    }

    if (body.detail != null) {
      message = asText(body.detail)
    }

    if (body.karyawan_id != null) {
      field = 'karyawan_id'
      message = asText(body.karyawan_id) || message
    } else if (body.password != null) {
      field = 'password'
      message = asText(body.password) || message
    }
  } else if (typeof data === 'string' && data.trim()) {
    message = data.length > 180 ? `Login gagal (HTTP ${err.response.status}).` : data
  }

  if (!field && message) {
    field = inferFieldFromMessage(message)
  }

  if (!message) {
    if (err.response.status === 401) {
      message = 'ID karyawan atau kata sandi salah.'
    } else if (err.response.status === 403) {
      message = 'Anda tidak memiliki akses.'
    } else {
      message = `Login gagal (HTTP ${err.response.status}).`
    }
  }

  if (message.toLowerCase().includes('api key')) {
    return {
      message:
        'Kunci API tidak valid. Pastikan frontend dibuild dengan API_KEY yang sama dengan backend.',
    }
  }

  return { message, field }
}

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
    // DRF validation: { field: ["msg"] } or { detail: "..." already handled }
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
  if (
    lower.includes('tidak ditemukan') ||
    lower.includes('id karyawan') ||
    lower.includes('username') ||
    lower.includes('unknown user')
  ) {
    // Prefer username when the API message is about the id existing
    if (lower.includes('kata sandi') && !lower.includes('tidak ditemukan')) {
      return 'password'
    }
    if (lower.includes('tidak ditemukan') || lower.includes('belum terdaftar')) {
      return 'karyawan_id'
    }
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

/**
 * Read a structured login failure from an axios/network error so the login
 * form can highlight either ID karyawan or password.
 */
export function parseLoginError(err: unknown): ParsedLoginError {
  if (!axios.isAxiosError(err)) {
    return { message: 'Login gagal. Coba lagi.' }
  }

  // Request never reached the API (CORS, wrong host, offline, etc.).
  if (!err.response) {
    return {
      message:
        'Tidak dapat terhubung ke server. Periksa koneksi atau alamat API.',
    }
  }

  const data = err.response.data
  let message = ''
  let field: LoginField | undefined

  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const body = data as Record<string, unknown>
    field = normalizeField(body.field)

    // Prefer machine-readable code from the backend login view.
    if (body.code === 'invalid_username' || body.code === 'missing_username') {
      field = 'karyawan_id'
    } else if (body.code === 'invalid_password') {
      field = 'password'
    }

    if (body.detail != null) {
      message = asText(body.detail)
    }

    // Serializer field errors: { karyawan_id: ["..."], password: ["..."] }
    if (body.karyawan_id != null) {
      field = 'karyawan_id'
      message = asText(body.karyawan_id) || message
    } else if (body.password != null) {
      field = 'password'
      message = asText(body.password) || message
    }
  } else if (typeof data === 'string' && data.trim()) {
    // Nginx / plain-text error page body
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

  // Map API-key auth failures to a clear non-credential message.
  if (message.toLowerCase().includes('api key')) {
    return {
      message:
        'Kunci API tidak valid. Pastikan frontend dibuild dengan API_KEY yang sama dengan backend.',
    }
  }

  return { message, field }
}

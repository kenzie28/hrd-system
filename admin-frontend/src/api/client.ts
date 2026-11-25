import axios from 'axios'

import { GAJI_PASSWORD_HEADER, readGajiPassword } from '../gajiPassword'

export const ADMIN_TOKEN_STORAGE_KEY = 'admin_token'

/**
 * Resolve API base URL.
 * - In the browser: always same-origin `/api` (Docker nginx or Vite dev proxy).
 * - Absolute `VITE_API_URL` only used when it looks like http(s):// (rare overrides).
 */
function resolveApiBaseUrl(): string {
  const env = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (env && /^https?:\/\//i.test(env)) {
    return env.replace(/\/$/, '')
  }
  return '/api'
}

export const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: {
    ...(import.meta.env.VITE_API_KEY
      ? { 'X-Api-Key': import.meta.env.VITE_API_KEY }
      : {}),
  },
})

function isGajiRequest(url: string | undefined): boolean {
  if (!url) return false
  return url.includes('/admin/gaji')
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  if (isGajiRequest(config.url)) {
    const password = readGajiPassword()
    if (password) {
      config.headers[GAJI_PASSWORD_HEADER] = password
    }
  }
  return config
})

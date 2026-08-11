import axios from 'axios'

export const TOKEN_STORAGE_KEY = 'portal_token'

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

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

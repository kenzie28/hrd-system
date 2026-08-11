import axios from 'axios'

export const TOKEN_STORAGE_KEY = 'portal_token'

// Default to same-origin /api (Docker nginx proxy). Vite local dev can override
// with VITE_API_URL=http://localhost:8028/api.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
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

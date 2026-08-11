import axios from 'axios'

export const TOKEN_STORAGE_KEY = 'portal_token'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
  headers: {
    'X-Api-Key': import.meta.env.VITE_API_KEY ?? '',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

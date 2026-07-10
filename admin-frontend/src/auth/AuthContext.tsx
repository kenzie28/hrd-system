import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { ADMIN_TOKEN_STORAGE_KEY, api } from '../api/client'
import type { AdminKaryawan, AdminLoginResponse } from '../api/types'

interface AuthContextValue {
  karyawan: AdminKaryawan | null
  loading: boolean
  isAuthenticated: boolean
  login: (karyawanId: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [karyawan, setKaryawan] = useState<AdminKaryawan | null>(null)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY)
    setKaryawan(null)
  }, [])

  useEffect(() => {
    const token = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get<AdminKaryawan>('/admin/me/')
      .then(({ data }) => setKaryawan(data))
      .catch(() => {
        localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY)
        setKaryawan(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (karyawanId: string, password: string) => {
    const { data } = await api.post<AdminLoginResponse>('/admin/login/', {
      karyawan_id: karyawanId,
      password,
    })
    localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, data.token)
    setKaryawan(data.karyawan)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      karyawan,
      loading,
      isAuthenticated: karyawan !== null,
      login,
      logout,
    }),
    [karyawan, loading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (ctx === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}

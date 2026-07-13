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
import type {
  AdminKaryawan,
  AdminLoginResponse,
  ChangePasswordResponse,
} from '../api/types'

interface AuthContextValue {
  karyawan: AdminKaryawan | null
  mustChangePassword: boolean
  loading: boolean
  isAuthenticated: boolean
  login: (karyawanId: string, password: string) => Promise<void>
  changePassword: (newPassword: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [karyawan, setKaryawan] = useState<AdminKaryawan | null>(null)
  const [mustChangePassword, setMustChangePassword] = useState(false)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY)
    setKaryawan(null)
    setMustChangePassword(false)
  }, [])

  useEffect(() => {
    const token = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get<AdminKaryawan>('/admin/me/')
      .then(({ data }) => {
        setKaryawan(data)
        setMustChangePassword(data.must_change_password)
      })
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
    setMustChangePassword(data.karyawan.must_change_password)
  }, [])

  const changePassword = useCallback(async (newPassword: string) => {
    const { data } = await api.post<ChangePasswordResponse>(
      '/portal/change-password/',
      { new_password: newPassword },
    )
    localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, data.token)
    setMustChangePassword(data.must_change_password)
    setKaryawan((prev) =>
      prev ? { ...prev, must_change_password: data.must_change_password } : prev,
    )
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      karyawan,
      mustChangePassword,
      loading,
      isAuthenticated: karyawan !== null,
      login,
      changePassword,
      logout,
    }),
    [karyawan, mustChangePassword, loading, login, changePassword, logout],
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

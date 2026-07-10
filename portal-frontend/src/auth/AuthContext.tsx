import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, TOKEN_STORAGE_KEY } from '../api/client'
import type {
  ChangePasswordResponse,
  LoginResponse,
  PortalKaryawan,
} from '../api/types'

interface AuthContextValue {
  karyawan: PortalKaryawan | null
  mustChangePassword: boolean
  loading: boolean
  isAuthenticated: boolean
  login: (karyawanId: string, password: string) => Promise<void>
  changePassword: (newPassword: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [karyawan, setKaryawan] = useState<PortalKaryawan | null>(null)
  const [mustChangePassword, setMustChangePassword] = useState(false)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setKaryawan(null)
    setMustChangePassword(false)
  }, [])

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get<PortalKaryawan>('/portal/me/')
      .then(({ data }) => {
        setKaryawan(data)
        setMustChangePassword(data.must_change_password)
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        setKaryawan(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (karyawanId: string, password: string) => {
    const { data } = await api.post<LoginResponse>('/portal/login/', {
      karyawan_id: karyawanId,
      password,
    })
    localStorage.setItem(TOKEN_STORAGE_KEY, data.token)
    setKaryawan(data.karyawan)
    setMustChangePassword(data.must_change_password)
  }, [])

  const changePassword = useCallback(async (newPassword: string) => {
    const { data } = await api.post<ChangePasswordResponse>(
      '/portal/change-password/',
      { new_password: newPassword },
    )
    localStorage.setItem(TOKEN_STORAGE_KEY, data.token)
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

import { Spin } from 'antd'
import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, mustChangePassword, loading } = useAuth()

  if (loading) {
    return (
      <div className="admin-centered">
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (mustChangePassword) {
    return <Navigate to="/change-password" replace />
  }

  return <>{children}</>
}

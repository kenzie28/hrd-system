import { Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from './components/AdminLayout'
import ProtectedRoute from './components/ProtectedRoute'
import AbsensiPage from './pages/AbsensiPage'
import CutiPage from './pages/CutiPage'
import GajiPage from './pages/GajiPage'
import HomePage from './pages/HomePage'
import ChangePasswordPage from './pages/ChangePasswordPage'
import LoginPage from './pages/LoginPage'
import ResetPasswordPage from './pages/ResetPasswordPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/change-password" element={<ChangePasswordPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<HomePage />} />
        <Route path="/absensi" element={<AbsensiPage />} />
        <Route path="/cuti" element={<CutiPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/gaji" element={<GajiPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import PortalLayout from './components/PortalLayout'
import LoginPage from './pages/LoginPage'
import ChangePasswordPage from './pages/ChangePasswordPage'
import HomePage from './pages/HomePage'
import GajiPage from './pages/GajiPage'
import GajiBreakdownPage from './pages/GajiBreakdownPage'
import CutiPage from './pages/CutiPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/change-password" element={<ChangePasswordPage />} />
      <Route
        element={
          <ProtectedRoute>
            <PortalLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<HomePage />} />
        <Route path="/gaji" element={<GajiPage />} />
        <Route path="/gaji/:bulan" element={<GajiBreakdownPage />} />
        <Route path="/cuti" element={<CutiPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

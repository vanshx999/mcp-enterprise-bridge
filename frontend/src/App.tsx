import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'

function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (user?.role !== 'admin') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import PendingApprovals from './pages/PendingApprovals'
import AuditLog from './pages/AuditLog'
import ApiKeys from './pages/ApiKeys'
import Permissions from './pages/Permissions'
import Analytics from './pages/Analytics'
import Databases from './pages/Databases'
import ApprovalTemplates from './pages/ApprovalTemplates'
import QueryTemplates from './pages/QueryTemplates'
import Users from './pages/Users'
import Navbar from './components/Navbar'
import ToastContainer from './components/ToastContainer'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="min-h-screen bg-zinc-950">
                <Navbar />
                <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                  <Routes>
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/approvals" element={<PendingApprovals />} />
                    <Route path="/audit" element={<AuditLog />} />
                    <Route path="/keys" element={<ApiKeys />} />
                    <Route path="/permissions" element={<Permissions />} />
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/databases" element={<Databases />} />
                    <Route path="/templates" element={<ApprovalTemplates />} />
                    <Route path="/query-templates" element={<QueryTemplates />} />
                    <Route path="/users" element={<AdminRoute><Users /></AdminRoute>} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </main>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

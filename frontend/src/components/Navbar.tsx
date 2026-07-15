import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-accent-50 text-accent-700'
        : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
    }`

  return (
    <nav className="bg-zinc-900 border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-14 items-center">
          <div className="flex items-center gap-6">
            <span className="text-base font-bold text-white tracking-tight">
              mcp<span className="text-accent-400">bridge</span>
            </span>
            <div className="flex gap-0.5">
              <NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink>
              <NavLink to="/approvals" className={linkClass}>Approvals</NavLink>
              <NavLink to="/permissions" className={linkClass}>Permissions</NavLink>
              <NavLink to="/audit" className={linkClass}>Audit Log</NavLink>
              <NavLink to="/analytics" className={linkClass}>Analytics</NavLink>
              <NavLink to="/databases" className={linkClass}>Databases</NavLink>
              <NavLink to="/templates" className={linkClass}>Approval Templates</NavLink>
              <NavLink to="/query-templates" className={linkClass}>Query Templates</NavLink>
              {isAdmin && <NavLink to="/users" className={linkClass}>Users</NavLink>}
              <NavLink to="/keys" className={linkClass}>API Keys</NavLink>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-500">
              {user?.full_name || user?.email}
            </span>
            <button onClick={logout} className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}

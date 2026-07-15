import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface User {
  id: string
  email: string
  role: string
  full_name: string | null
  is_active: boolean
  password_change_required: boolean
  created_at: string
}

const roleColors: Record<string, string> = {
  admin: 'bg-purple-900/40 text-purple-300 border-purple-700/30',
  approver: 'bg-amber-900/40 text-amber-300 border-amber-700/30',
  viewer: 'bg-zinc-800 text-zinc-400 border-zinc-700',
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'approver' })

  const fetchUsers = async () => {
    try { setUsers(await api.get<User[]>('/api/users')) } catch {}
  }

  useEffect(() => { fetchUsers() }, [])

  const openNew = () => {
    setEditing(null)
    setForm({ email: '', password: '', full_name: '', role: 'approver' })
    setShowModal(true)
  }

  const createUser = async () => {
    try {
      await api.post('/api/users', form)
      setShowModal(false)
      fetchUsers()
    } catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  const toggleActive = async (user: User) => {
    if (!confirm(`${user.is_active ? 'Deactivate' : 'Activate'} ${user.email}?`)) return
    try {
      await api.put(`/api/users/${user.id}`, { is_active: !user.is_active })
      fetchUsers()
    } catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  const changeRole = async (user: User, role: string) => {
    try {
      await api.put(`/api/users/${user.id}`, { role })
      fetchUsers()
    } catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Users</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Manage user accounts and roles</p>
        </div>
        <button onClick={openNew}
          className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors">
          + New User
        </button>
      </div>

      <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-zinc-800">
                {['Email', 'Name', 'Role', 'Status', 'Created', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3 text-sm text-zinc-200 font-mono">{u.email}</td>
                  <td className="px-4 py-3 text-sm text-zinc-400">{u.full_name || '-'}</td>
                  <td className="px-4 py-3">
                    <select value={u.role} onChange={e => changeRole(u, e.target.value)}
                      className="bg-transparent text-sm font-medium focus:outline-none cursor-pointer">
                      {['admin', 'approver', 'viewer'].map(r => (
                        <option key={r} value={r} className="bg-zinc-900">{r}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-red-500'}`} />
                      <span className={`text-xs ${u.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                      {u.password_change_required && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-900/30 text-amber-300">reset</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-500">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => toggleActive(u)}
                      className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors mr-3">
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-zinc-600">No users found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-base font-semibold text-zinc-100 mb-4">New User</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Email</label>
                <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  placeholder="user@example.com"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Password</label>
                <input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  placeholder="Min 8 characters"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Full Name</label>
                <input type="text" value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                  placeholder="Optional"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Role</label>
                <select value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500">
                  <option value="admin">Admin</option>
                  <option value="approver">Approver</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
              <button onClick={createUser} disabled={!form.email || form.password.length < 8}
                className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40">Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

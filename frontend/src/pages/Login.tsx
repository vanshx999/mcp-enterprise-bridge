import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const [email, setEmail] = useState('admin@mcpbridge.io')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [ssoEnabled, setSsoEnabled] = useState(false)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const setAuth = useAuthStore((s) => s.setAuth)
  const token = useAuthStore((s) => s.token)

  useEffect(() => {
    const tokenParam = searchParams.get('token')
    const emailParam = searchParams.get('email')
    const roleParam = searchParams.get('role')
    const nameParam = searchParams.get('name')
    if (tokenParam) {
      setAuth(tokenParam, {
        id: '',
        email: emailParam || '',
        role: roleParam || 'approver',
        full_name: nameParam || emailParam || '',
      })
      navigate('/dashboard', { replace: true })
    }
  }, [searchParams, setAuth, navigate])

  useEffect(() => {
    api.get<{ sso_enabled: boolean }>('/api/auth/sso/status').then((r) => setSsoEnabled(r.sso_enabled)).catch(() => {})
  }, [])

  if (token) { navigate('/dashboard', { replace: true }); return null }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post<{ access_token: string; user: { id: string; email: string; role: string; full_name: string } }>(
        '/api/auth/login', { email, password }
      )
      setAuth(res.access_token, res.user)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="bg-zinc-900/50 rounded-xl border border-zinc-800 p-8 w-full max-w-sm">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-white">mcp<span className="text-accent-400">bridge</span></h1>
          <p className="text-sm text-zinc-500 mt-1">Enterprise approval dashboard</p>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-800/40 text-red-300 text-sm rounded-lg px-4 py-3 mb-4">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1 uppercase tracking-wider">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500" required />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1 uppercase tracking-wider">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500" required />
          </div>
          <button type="submit" disabled={loading}
            className="w-full px-4 py-2.5 bg-accent-600 hover:bg-accent-500 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50">
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        {ssoEnabled && (
          <>
            <div className="relative my-5">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-zinc-700" /></div>
              <div className="relative flex justify-center"><span className="bg-zinc-900/50 px-2 text-xs text-zinc-500">or</span></div>
            </div>
            <a href="/api/auth/sso/login"
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm font-medium rounded-lg border border-zinc-700 transition-colors">
              Sign in with SSO
            </a>
          </>
        )}

        <p className="mt-5 text-center text-xs text-zinc-500">
          No account?{' '}
          <Link to="/signup" className="text-accent-400 hover:text-accent-300 transition-colors">Create one</Link>
        </p>
      </div>
    </div>
  )
}

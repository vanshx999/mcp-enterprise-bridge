import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface Database {
  id: string
  name: string
  db_type: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function Databases() {
  const [dbs, setDbs] = useState<Database[]>([])
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ name: '', connection_url: '', db_type: 'postgresql' })
  const [testing, setTesting] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ id: string; success: boolean; message: string } | null>(null)

  const fetchDbs = async () => {
    try { setDbs(await api.get<Database[]>('/api/databases')) } catch {}
  }

  useEffect(() => { fetchDbs() }, [])

  const register = async () => {
    try {
      await api.post('/api/databases', form)
      setShowModal(false)
      setForm({ name: '', connection_url: '', db_type: 'postgresql' })
      fetchDbs()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed')
    }
  }

  const remove = async (id: string) => {
    if (!confirm('Unregister this database? Connection pools will be closed.')) return
    try { await api.delete(`/api/databases/${id}`); fetchDbs() }
    catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  const testConnection = async (id: string) => {
    setTesting(id)
    setTestResult(null)
    try {
      await api.post(`/api/databases/${id}/test`)
      setTestResult({ id, success: true, message: 'Connection successful' })
    } catch (e) {
      setTestResult({ id, success: false, message: e instanceof Error ? e.message : 'Failed' })
    } finally {
      setTesting(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Databases</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Register and manage database connections</p>
        </div>
        <button onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors">
          + Register Database
        </button>
      </div>

      <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 overflow-hidden">
        <div className="divide-y divide-zinc-800/50">
          {dbs.map(db => (
            <div key={db.id} className="px-5 py-4 flex items-center gap-4">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className={`w-2 h-2 rounded-full shrink-0 ${db.is_active ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-zinc-200">{db.name}</span>
                    <span className="text-xs font-mono text-zinc-500 uppercase">{db.db_type}</span>
                    {!db.is_active && <span className="text-xs text-zinc-600">(inactive)</span>}
                  </div>
                  <p className="text-xs text-zinc-500 mt-0.5">Registered {new Date(db.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              {testResult?.id === db.id && (
                <span className={`text-xs ${testResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
                  {testResult.message}
                </span>
              )}
              <button onClick={() => testConnection(db.id)} disabled={testing === db.id}
                className="text-xs text-zinc-500 hover:text-accent-400 transition-colors disabled:opacity-40">
                {testing === db.id ? 'Testing...' : 'Test'}
              </button>
              <button onClick={() => remove(db.id)}
                className="text-xs text-zinc-500 hover:text-red-400 transition-colors">Remove</button>
            </div>
          ))}
          {dbs.length === 0 && (
            <div className="px-5 py-8 text-center text-sm text-zinc-600">No databases registered</div>
          )}
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-base font-semibold text-zinc-100 mb-4">Register Database</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Name</label>
                <input type="text" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. production-db"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Connection URL</label>
                <input type="text" value={form.connection_url} onChange={e => setForm(f => ({ ...f, connection_url: e.target.value }))}
                  placeholder="postgresql://user:pass@host:5432/db"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Database Type</label>
                <select value={form.db_type} onChange={e => setForm(f => ({ ...f, db_type: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500">
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlite">SQLite</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
              <button onClick={register} disabled={!form.name || !form.connection_url}
                className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40">Register</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

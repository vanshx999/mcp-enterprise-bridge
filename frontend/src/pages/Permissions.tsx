import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface Permission {
  id: string
  agent_id: string
  tool_name: string
  resource_pattern: string
  risk_level: string
  auto_approve: boolean
  created_at: string
}

const riskColors: Record<string, string> = {
  low: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/30',
  medium: 'bg-amber-900/40 text-amber-300 border-amber-700/30',
  high: 'bg-red-900/40 text-red-300 border-red-700/30',
}

const tools = ['execute_query', 'list_tables', 'describe_schema']

export default function Permissions() {
  const [perms, setPerms] = useState<Permission[]>([])
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<Permission | null>(null)
  const [form, setForm] = useState({ agent_id: '', tool_name: 'execute_query', resource_pattern: '*', risk_level: 'low', auto_approve: false })

  const fetch = async () => {
    try { setPerms(await api.get<Permission[]>('/api/permissions')) } catch {}
  }

  useEffect(() => { fetch() }, [])

  const openNew = () => {
    setEditing(null)
    setForm({ agent_id: '', tool_name: 'execute_query', resource_pattern: '*', risk_level: 'low', auto_approve: false })
    setShowModal(true)
  }

  const openEdit = (p: Permission) => {
    setEditing(p)
    setForm({ agent_id: p.agent_id, tool_name: p.tool_name, resource_pattern: p.resource_pattern, risk_level: p.risk_level, auto_approve: p.auto_approve })
    setShowModal(true)
  }

  const save = async () => {
    try {
      if (editing) {
        const updates: any = {}
        if (form.resource_pattern !== editing.resource_pattern) updates.resource_pattern = form.resource_pattern
        if (form.risk_level !== editing.risk_level) updates.risk_level = form.risk_level
        if (form.auto_approve !== editing.auto_approve) updates.auto_approve = form.auto_approve
        if (Object.keys(updates).length) await api.put(`/api/permissions/${editing.id}`, updates)
      } else {
        await api.post('/api/permissions', form)
      }
      setShowModal(false)
      fetch()
    } catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  const remove = async (id: string) => {
    if (!confirm('Delete this permission?')) return
    try { await api.delete(`/api/permissions/${id}`); fetch() }
    catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Permissions</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Which agents can call which tools</p>
        </div>
        <button onClick={openNew}
          className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors">
          + New Permission
        </button>
      </div>

      <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-zinc-800">
                {['Agent', 'Tool', 'Risk', 'Pattern', 'Auto-Approve', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {perms.map(p => (
                <tr key={p.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3 text-sm font-mono text-zinc-200">{p.agent_id}</td>
                  <td className="px-4 py-3 text-sm font-mono text-accent-400">{p.tool_name}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${riskColors[p.risk_level] || riskColors.low}`}>
                      {p.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-400 font-mono">{p.resource_pattern}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-mono ${p.auto_approve ? 'text-emerald-400' : 'text-zinc-500'}`}>
                      {p.auto_approve ? 'yes' : 'no'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(p)} className="text-xs text-zinc-500 hover:text-accent-400 transition-colors">Edit</button>
                      <button onClick={() => remove(p.id)} className="text-xs text-zinc-500 hover:text-red-400 transition-colors">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {perms.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-zinc-600">No permissions configured</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-base font-semibold text-zinc-100 mb-4">{editing ? 'Edit Permission' : 'New Permission'}</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Agent ID</label>
                <input type="text" value={form.agent_id} onChange={e => setForm(f => ({ ...f, agent_id: e.target.value }))}
                  disabled={!!editing}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Tool</label>
                <select value={form.tool_name} onChange={e => setForm(f => ({ ...f, tool_name: e.target.value }))}
                  disabled={!!editing}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-accent-500">
                  {tools.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Risk Level</label>
                <select value={form.risk_level} onChange={e => setForm(f => ({ ...f, risk_level: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Resource Pattern</label>
                <input type="text" value={form.resource_pattern} onChange={e => setForm(f => ({ ...f, resource_pattern: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <label className="flex items-center gap-2 text-sm text-zinc-300">
                <input type="checkbox" checked={form.auto_approve} onChange={e => setForm(f => ({ ...f, auto_approve: e.target.checked }))}
                  className="rounded border-zinc-600 bg-zinc-800 text-accent-600 focus:ring-accent-500" />
                Auto-approve (skip HITL)
              </label>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
              <button onClick={save} disabled={!form.agent_id}
                className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40">
                {editing ? 'Save' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

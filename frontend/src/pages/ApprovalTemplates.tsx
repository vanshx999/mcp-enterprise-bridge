import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface Template {
  id: string
  name: string
  description: string
  tool_name: string
  resource_pattern: string
  risk_level: string
  auto_approve: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

const riskColors: Record<string, string> = {
  low: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/30',
  medium: 'bg-amber-900/40 text-amber-300 border-amber-700/30',
  high: 'bg-red-900/40 text-red-300 border-red-700/30',
}

const tools = ['execute_query', 'list_tables', 'describe_schema']

export default function ApprovalTemplates() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [showModal, setShowModal] = useState(false)
  const [showApplyModal, setShowApplyModal] = useState(false)
  const [applyTemplateId, setApplyTemplateId] = useState('')
  const [applyAgentId, setApplyAgentId] = useState('')
  const [editing, setEditing] = useState<Template | null>(null)
  const [form, setForm] = useState({ name: '', description: '', tool_name: 'execute_query', resource_pattern: '*', risk_level: 'medium', auto_approve: false })

  const fetch = async () => {
    try { setTemplates(await api.get<Template[]>('/api/approval-templates')) } catch {}
  }

  useEffect(() => { fetch() }, [])

  const openNew = () => {
    setEditing(null)
    setForm({ name: '', description: '', tool_name: 'execute_query', resource_pattern: '*', risk_level: 'medium', auto_approve: false })
    setShowModal(true)
  }

  const openEdit = (t: Template) => {
    setEditing(t)
    setForm({ name: t.name, description: t.description, tool_name: t.tool_name, resource_pattern: t.resource_pattern, risk_level: t.risk_level, auto_approve: t.auto_approve })
    setShowModal(true)
  }

  const save = async () => {
    try {
      if (editing) {
        const updates: any = {}
        if (form.description !== editing.description) updates.description = form.description
        if (form.tool_name !== editing.tool_name) updates.tool_name = form.tool_name
        if (form.resource_pattern !== editing.resource_pattern) updates.resource_pattern = form.resource_pattern
        if (form.risk_level !== editing.risk_level) updates.risk_level = form.risk_level
        if (form.auto_approve !== editing.auto_approve) updates.auto_approve = form.auto_approve
        if (Object.keys(updates).length) await api.put(`/api/approval-templates/${editing.id}`, updates)
      } else {
        await api.post('/api/approval-templates', form)
      }
      setShowModal(false)
      fetch()
    } catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  const remove = async (id: string) => {
    if (!confirm('Delete this template?')) return
    try { await api.delete(`/api/approval-templates/${id}`); fetch() }
    catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  const openApply = (id: string) => {
    setApplyTemplateId(id)
    setApplyAgentId('')
    setShowApplyModal(true)
  }

  const applyTemplate = async () => {
    if (!applyAgentId.trim()) return
    try {
      await api.post(`/api/approval-templates/${applyTemplateId}/apply?agent_id=${encodeURIComponent(applyAgentId)}`)
      setShowApplyModal(false)
      alert('Template applied successfully')
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Approval Templates</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Pre-configured permission presets</p>
        </div>
        <button onClick={openNew}
          className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors">
          + New Template
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {templates.map(t => (
          <div key={t.id} className="bg-zinc-900/40 rounded-xl border border-zinc-800 p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className={`inline-block w-2 h-2 rounded-full ${t.is_active ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
                  <span className="text-sm font-semibold text-zinc-100">{t.name}</span>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border ${riskColors[t.risk_level]}`}>{t.risk_level}</span>
                </div>
                {t.description && <p className="text-xs text-zinc-500 mt-1">{t.description}</p>}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-mono">
              <span className="px-2 py-0.5 rounded bg-zinc-800 text-accent-400">{t.tool_name}</span>
              <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">{t.resource_pattern}</span>
              {t.auto_approve && <span className="px-2 py-0.5 rounded bg-emerald-900/30 text-emerald-300">auto-approve</span>}
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={() => openApply(t.id)}
                className="flex-1 px-3 py-1.5 bg-accent-600 hover:bg-accent-500 text-white text-xs font-medium rounded-lg transition-colors">Apply to Agent</button>
              <button onClick={() => openEdit(t)}
                className="px-3 py-1.5 text-xs text-zinc-500 hover:text-accent-400 transition-colors">Edit</button>
              <button onClick={() => remove(t.id)}
                className="px-3 py-1.5 text-xs text-zinc-500 hover:text-red-400 transition-colors">Delete</button>
            </div>
          </div>
        ))}
        {templates.length === 0 && (
          <div className="col-span-full bg-zinc-900/30 rounded-xl border border-zinc-800 py-12 text-center text-sm text-zinc-600">
            No templates configured
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-base font-semibold text-zinc-100 mb-4">{editing ? 'Edit Template' : 'New Template'}</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Name</label>
                <input type="text" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  disabled={!!editing}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Description</label>
                <input type="text" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Optional description"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Tool</label>
                <select value={form.tool_name} onChange={e => setForm(f => ({ ...f, tool_name: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500">
                  {tools.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Resource Pattern</label>
                <input type="text" value={form.resource_pattern} onChange={e => setForm(f => ({ ...f, resource_pattern: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500" />
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
              <label className="flex items-center gap-2 text-sm text-zinc-300">
                <input type="checkbox" checked={form.auto_approve} onChange={e => setForm(f => ({ ...f, auto_approve: e.target.checked }))}
                  className="rounded border-zinc-600 bg-zinc-800 text-accent-600 focus:ring-accent-500" />
                Auto-approve
              </label>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
              <button onClick={save} disabled={!form.name}
                className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40">
                {editing ? 'Save' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showApplyModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-base font-semibold text-zinc-100 mb-4">Apply Template to Agent</h3>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Agent ID</label>
              <input type="text" value={applyAgentId} onChange={e => setApplyAgentId(e.target.value)}
                placeholder="e.g. default-agent"
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500" />
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setShowApplyModal(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
              <button onClick={applyTemplate} disabled={!applyAgentId.trim()}
                className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40">Apply</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

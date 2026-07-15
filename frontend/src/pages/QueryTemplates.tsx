import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

interface QueryTemplate {
  id: string
  name: string
  description: string
  query_text: string
  parameters: { name: string; type: string; default?: string }[]
  agent_id: string | null
  created_by: string
  created_at: string
  updated_at: string
}

const emptyForm = { name: '', description: '', query_text: '', parameters: '', agent_id: '' }

export default function QueryTemplates() {
  const [templates, setTemplates] = useState<QueryTemplate[]>([])
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<QueryTemplate | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)

  const fetchTemplates = useCallback(async () => {
    try { setTemplates(await api.get<QueryTemplate[]>('/api/query-templates')) } catch {}
  }, [])

  useEffect(() => { fetchTemplates() }, [fetchTemplates])

  const openCreate = () => {
    setEditing(null)
    setForm(emptyForm)
    setShowModal(true)
  }

  const openEdit = (t: QueryTemplate) => {
    setEditing(t)
    setForm({
      name: t.name,
      description: t.description,
      query_text: t.query_text,
      parameters: JSON.stringify(t.parameters, null, 2),
      agent_id: t.agent_id || '',
    })
    setShowModal(true)
  }

  const save = async () => {
    if (!form.name.trim() || !form.query_text.trim()) return
    setSaving(true)
    try {
      let params: any[] = []
      try { params = JSON.parse(form.parameters) } catch { params = [] }
      const body = { name: form.name, description: form.description, query_text: form.query_text, parameters: params, agent_id: form.agent_id || null }
      if (editing) await api.put(`/api/query-templates/${editing.id}`, body)
      else await api.post('/api/query-templates', body)
      setShowModal(false)
      fetchTemplates()
    } catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
    finally { setSaving(false) }
  }

  const remove = async (id: string) => {
    if (!confirm('Delete this template?')) return
    try { await api.delete(`/api/query-templates/${id}`); fetchTemplates() }
    catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Query Templates</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Save and reuse parameterized queries</p>
        </div>
        <button onClick={openCreate}
          className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors">
          + New Template
        </button>
      </div>

      {templates.length === 0 ? (
        <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 py-16 text-center">
          <p className="text-zinc-600 text-sm">No query templates yet</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {templates.map((t) => (
            <div key={t.id} className="bg-zinc-900/40 rounded-xl border border-zinc-800 p-5 hover:border-zinc-700 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">{t.name}</h3>
                  {t.description && <p className="text-xs text-zinc-500 mt-0.5">{t.description}</p>}
                </div>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(t)}
                    className="text-xs text-zinc-500 hover:text-accent-400 transition-colors px-2 py-1">Edit</button>
                  <button onClick={() => remove(t.id)}
                    className="text-xs text-red-500 hover:text-red-400 transition-colors px-2 py-1">Delete</button>
                </div>
              </div>
              <pre className="bg-black/40 rounded-lg p-3 text-xs text-zinc-400 overflow-x-auto max-h-24 mb-2 font-mono">{t.query_text}</pre>
              <div className="flex items-center gap-2 text-[10px] text-zinc-600">
                {t.parameters.length > 0 && <span>{t.parameters.length} param{t.parameters.length > 1 ? 's' : ''}</span>}
                {t.agent_id && <span>Agent: {t.agent_id}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-2xl w-full mx-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-semibold text-zinc-100 mb-4">{editing ? 'Edit Template' : 'New Template'}</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Name *</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Description</label>
                <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Query Text *</label>
                <textarea value={form.query_text} onChange={(e) => setForm({ ...form, query_text: e.target.value })}
                  className="w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 font-mono focus:outline-none focus:ring-2 focus:ring-accent-500 min-h-[100px]"
                  placeholder="SELECT * FROM users WHERE id = :id" />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Parameters (JSON array)</label>
                <textarea value={form.parameters} onChange={(e) => setForm({ ...form, parameters: e.target.value })}
                  className="w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 font-mono focus:outline-none focus:ring-2 focus:ring-accent-500 min-h-[80px]"
                  placeholder='[{"name": "id", "type": "string"}]' />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Agent ID (optional)</label>
                <input value={form.agent_id} onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
                  className="w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <button onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
              <button onClick={save} disabled={saving || !form.name.trim() || !form.query_text.trim()}
                className="px-4 py-2 text-sm font-medium rounded-lg text-white bg-accent-600 hover:bg-accent-500 transition-colors disabled:opacity-40">
                {saving ? 'Saving...' : editing ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

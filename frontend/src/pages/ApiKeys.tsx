import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface AgentKey {
  id: string
  agent_id: string
  key_prefix: string
  label: string
  is_active: boolean
  created_at: string
  last_used_at: string | null
}

export default function ApiKeys() {
  const [keys, setKeys] = useState<AgentKey[]>([])
  const [newKey, setNewKey] = useState<{ key: string; agent_id: string } | null>(null)
  const [agentId, setAgentId] = useState('default-agent')
  const [label, setLabel] = useState('')
  const [showNew, setShowNew] = useState(false)

  const fetchKeys = async () => {
    try { setKeys(await api.get<AgentKey[]>('/api/agent/keys')) } catch {}
  }

  useEffect(() => { fetchKeys() }, [])

  const createKey = async () => {
    try {
      const result = await api.post<{ key: string; agent_id: string; label: string }>('/api/agent/keys', { agent_id: agentId, label })
      setNewKey(result)
      setShowNew(false)
      setLabel('')
      fetchKeys()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed')
    }
  }

  const revokeKey = async (id: string) => {
    if (!confirm('Revoke this key? This cannot be undone.')) return
    try {
      await api.delete(`/api/agent/keys/${id}`)
      fetchKeys()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">API Keys</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Manage agent authentication keys</p>
        </div>
        <button onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors">
          + New Key
        </button>
      </div>

      {newKey && (
        <div className="bg-emerald-900/30 border border-emerald-700/40 rounded-xl p-5">
          <p className="text-sm font-semibold text-emerald-300 mb-2">Key Created — Copy it now, it won't be shown again</p>
          <div className="bg-black/40 rounded-lg p-3 font-mono text-sm text-zinc-200 break-all select-all">
            {newKey.key}
          </div>
          <p className="text-xs text-zinc-500 mt-2">Agent: <span className="font-mono text-zinc-400">{newKey.agent_id}</span></p>
          <button onClick={() => { navigator.clipboard?.writeText(newKey.key); setNewKey(null) }}
            className="mt-3 text-sm text-accent-400 hover:text-accent-300 transition-colors">Copy &amp; Close</button>
        </div>
      )}

      <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 overflow-hidden">
        <div className="divide-y divide-zinc-800/50">
          {keys.map((key) => (
            <div key={key.id} className="px-5 py-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`inline-block w-2 h-2 rounded-full ${key.is_active ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
                  <span className="text-sm font-medium text-zinc-200">{key.label || key.agent_id}</span>
                  <span className="text-xs font-mono text-zinc-500">{key.key_prefix}...</span>
                </div>
                <p className="text-xs text-zinc-500">
                  Agent: <span className="font-mono text-zinc-400">{key.agent_id}</span>
                  {key.last_used_at && <> &middot; Last used: {new Date(key.last_used_at).toLocaleString()}</>}
                  &middot; Created: {new Date(key.created_at).toLocaleDateString()}
                </p>
              </div>
              {key.is_active && (
                <button onClick={() => revokeKey(key.id)}
                  className="text-xs text-zinc-500 hover:text-red-400 transition-colors">Revoke</button>
              )}
            </div>
          ))}
          {keys.length === 0 && (
            <div className="px-5 py-8 text-center text-sm text-zinc-600">No API keys found</div>
          )}
        </div>
      </div>

      {showNew && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-base font-semibold text-zinc-100 mb-4">New API Key</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Agent ID</label>
                <input type="text" value={agentId} onChange={(e) => setAgentId(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Label</label>
                <input type="text" value={label} onChange={(e) => setLabel(e.target.value)}
                  placeholder="e.g. production-agent-v2"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setShowNew(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
              <button onClick={createKey}
                className="px-4 py-2 bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium rounded-lg transition-colors">Generate</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

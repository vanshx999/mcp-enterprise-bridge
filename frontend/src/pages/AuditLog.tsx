import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import AuditLogTable from '../components/AuditLogTable'
import StatusBadge from '../components/StatusBadge'

export default function AuditLog() {
  const [entries, setEntries] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [filters, setFilters] = useState({ agent_id: '', event_type: '' })
  const [selectedEntry, setSelectedEntry] = useState<any | null>(null)
  const [sessionTimeline, setSessionTimeline] = useState<any[]>([])

  const limit = 50

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: String(limit), offset: String(page * limit) })
      if (filters.agent_id) params.set('agent_id', filters.agent_id)
      if (filters.event_type) params.set('event_type', filters.event_type)
      const res = await api.get<{ total: number; data: any[] }>(`/api/audit/logs?${params.toString()}`)
      setEntries(res.data)
      setTotal(res.total)
    } catch {} finally { setLoading(false) }
  }, [page, filters])

  useEffect(() => { fetchLogs() }, [fetchLogs])

  const handleRowClick = async (entry: any) => {
    setSelectedEntry(entry)
    try { setSessionTimeline(await api.get<any[]>(`/api/audit/logs/${entry.session_id}`)) } catch { setSessionTimeline([]) }
  }

  const exportUrl = (fmt: string) => {
    const params = new URLSearchParams()
    if (filters.agent_id) params.set('agent_id', filters.agent_id)
    if (filters.event_type) params.set('event_type', filters.event_type)
    return `/api/audit/export/${fmt}?${params.toString()}`
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Audit Log</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Immutable record of every bridge action</p>
      </div>

      <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 p-4 flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Agent</label>
          <input type="text" value={filters.agent_id} onChange={(e) => { setFilters((f) => ({ ...f, agent_id: e.target.value })); setPage(0) }}
            placeholder="Filter by agent..." className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500 w-48" />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-500 mb-1 uppercase tracking-wider">Event Type</label>
          <select value={filters.event_type} onChange={(e) => { setFilters((f) => ({ ...f, event_type: e.target.value })); setPage(0) }}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-accent-500">
            <option value="">All</option>
            <option value="auto_approved">Auto Approved</option>
            <option value="approved_and_executed">Approved & Executed</option>
            <option value="denied">Denied</option>
            <option value="permission_denied">Permission Denied</option>
            <option value="timeout">Timeout</option>
            <option value="error">Error</option>
          </select>
        </div>
        <div className="flex gap-2 ml-auto">
          <a href={exportUrl('csv')}
            className="px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg transition-colors">
            Export CSV
          </a>
          <a href={exportUrl('json')}
            className="px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg transition-colors">
            Export JSON
          </a>
        </div>
      </div>

      <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-sm text-zinc-600">Loading...</div>
        ) : (
          <>
            <AuditLogTable entries={entries} onRowClick={handleRowClick} />
            <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-800">
              <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
                className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200 disabled:text-zinc-700 transition-colors">Previous</button>
              <span className="text-sm text-zinc-600">Page {page + 1} of {Math.max(1, totalPages)} ({total} total)</span>
              <button onClick={() => setPage((p) => p + 1)} disabled={page + 1 >= totalPages}
                className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200 disabled:text-zinc-700 transition-colors">Next</button>
            </div>
          </>
        )}
      </div>

      {selectedEntry && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-base font-semibold text-zinc-100">Session Timeline</h3>
                <p className="text-xs font-mono text-zinc-500 mt-0.5">{selectedEntry.session_id}</p>
              </div>
              <button onClick={() => { setSelectedEntry(null); setSessionTimeline([]) }}
                className="text-zinc-500 hover:text-zinc-300 transition-colors text-sm">Close</button>
            </div>
            <div className="space-y-2">
              {sessionTimeline.map((entry: any) => (
                <div key={entry.id} className={`flex items-start gap-3 p-3 rounded-lg ${
                  entry.event_type === 'denied' || entry.event_type === 'permission_denied'
                    ? 'bg-red-900/20 border border-red-800/30'
                    : entry.event_type === 'timeout'
                    ? 'bg-zinc-800/50 border border-zinc-700/30'
                    : 'bg-zinc-800/30'
                }`}>
                  <div className="text-xs text-zinc-500 font-mono whitespace-nowrap mt-0.5 w-16 shrink-0">
                    {new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={entry.event_type} />
                      {entry.tool_name && <span className="text-xs text-zinc-500 font-mono">{entry.tool_name}</span>}
                    </div>
                    {entry.result_summary && (
                      <p className={`text-xs mt-1 ${
                        entry.event_type === 'denied' || entry.event_type === 'permission_denied'
                          ? 'text-red-400'
                          : 'text-zinc-400'
                      }`}>{entry.result_summary}</p>
                    )}
                    {entry.metadata && typeof entry.metadata === 'object' && entry.metadata.risk_level && (
                      <div className="flex gap-2 mt-1.5">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          entry.metadata.risk_level === 'high' ? 'bg-red-900/40 text-red-300' :
                          entry.metadata.risk_level === 'medium' ? 'bg-amber-900/40 text-amber-300' :
                          'bg-emerald-900/40 text-emerald-300'
                        }`}>{entry.metadata.risk_level}</span>
                        {entry.metadata.auto_approve && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-medium bg-blue-900/40 text-blue-300">auto</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {sessionTimeline.length === 0 && (
                <p className="text-sm text-zinc-600 text-center py-4">No timeline entries found for this session</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

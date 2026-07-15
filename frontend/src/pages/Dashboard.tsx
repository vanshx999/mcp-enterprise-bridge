import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import StatusBadge from '../components/StatusBadge'

interface Stats {
  totalRequests: number
  pendingApprovals: number
  autoApproved: number
  denied: number
}

function StatCard({ label, value, accent, badge }: { label: string; value: number; accent: string; badge?: boolean }) {
  return (
    <div className="bg-zinc-900/50 rounded-xl border border-zinc-800 p-5 relative overflow-hidden">
      {badge && value > 0 && (
        <span className="absolute top-3 right-3 flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
        </span>
      )}
      <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{label}</p>
      <p className={`text-3xl font-bold mt-1.5 ${accent}`}>{value}</p>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({ totalRequests: 0, pendingApprovals: 0, autoApproved: 0, denied: 0 })
  const [recentLogs, setRecentLogs] = useState<any[]>([])

  const fetchData = useCallback(async () => {
    try {
      const [logsRes, pending] = await Promise.all([
        api.get<{ data: any[] }>('/api/audit/logs?limit=8'),
        api.get<any[]>('/api/approvals/pending'),
      ])
      const logs = logsRes.data
      setRecentLogs(logs)
      const today = new Date().toISOString().slice(0, 10)
      const todayLogs = logs.filter((l: any) => l.created_at?.startsWith(today))
      setStats({
        totalRequests: todayLogs.length,
        pendingApprovals: pending.length,
        autoApproved: todayLogs.filter((l: any) => l.event_type === 'auto_approved').length,
        denied: todayLogs.filter((l: any) => ['denied', 'permission_denied'].includes(l.event_type)).length,
      })
    } catch {}
  }, [])

  const handleMessage = useCallback((data: any) => {
    if (data.type === 'new_approval') setStats((s) => ({ ...s, pendingApprovals: s.pendingApprovals + 1 }))
    if (data.type === 'approval_resolved') fetchData()
  }, [fetchData])

  useWebSocket(handleMessage)
  useEffect(() => { fetchData() }, [fetchData])

  const cards = [
    { label: 'Requests Today', value: stats.totalRequests, accent: 'text-accent-400' },
    { label: 'Pending Approvals', value: stats.pendingApprovals, accent: 'text-amber-400', badge: true },
    { label: 'Auto-Approved', value: stats.autoApproved, accent: 'text-emerald-400' },
    { label: 'Denied', value: stats.denied, accent: 'text-red-400' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Real-time overview of bridge activity</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => <StatCard key={c.label} {...c} />)}
      </div>

      <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-zinc-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-100">Recent Activity</h2>
          <span className="text-xs text-zinc-500">{recentLogs.length} entries</span>
        </div>
        <div className="divide-y divide-zinc-800/50">
          {recentLogs.map((entry: any) => (
            <div key={entry.id} className="px-5 py-3 flex items-center gap-4 text-sm">
              <span className="text-xs text-zinc-500 font-mono w-16 shrink-0">
                {new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <StatusBadge status={entry.event_type} />
              <span className="text-zinc-300 font-mono text-xs truncate">{entry.agent_id || '-'}</span>
              <span className="text-zinc-500 text-xs truncate ml-auto">{entry.tool_name || ''}</span>
            </div>
          ))}
          {recentLogs.length === 0 && (
            <div className="px-5 py-8 text-center text-sm text-zinc-600">No activity yet</div>
          )}
        </div>
      </div>
    </div>
  )
}

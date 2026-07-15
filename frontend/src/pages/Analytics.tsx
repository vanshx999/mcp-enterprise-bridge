import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface AnalyticsSummary {
  total_queries: number
  total_approved: number
  total_denied: number
  total_approval_requests: number
  pending_approvals: number
  active_agents: number
  top_agents: { agent_id: string; query_count: number }[]
  queries_by_day: { day: string; count: number }[]
}

function BarChart({ data, labelKey, valueKey, maxValue, color }: {
  data: any[]
  labelKey: string
  valueKey: string
  maxValue: number
  color: string
}) {
  if (data.length === 0) return <p className="text-sm text-zinc-600 text-center py-8">No data</p>
  return (
    <div className="space-y-1.5">
      {data.map((item, i) => (
        <div key={i} className="flex items-center gap-3">
          <span className="text-xs text-zinc-400 font-mono w-28 truncate text-right shrink-0">
            {item[labelKey]}
          </span>
          <div className="flex-1 bg-zinc-800/50 rounded-full h-5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${color}`}
              style={{ width: `${(item[valueKey] / maxValue) * 100}%` }}
            />
          </div>
          <span className="text-xs text-zinc-500 font-mono w-8 shrink-0">{item[valueKey]}</span>
        </div>
      ))}
    </div>
  )
}

interface UsageEntry {
  agent_id: string
  tool_name: string
  count: number
  first_used: string
  last_used: string
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [usage, setUsage] = useState<UsageEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<'overview' | 'agents' | 'daily'>('overview')

  useEffect(() => {
    (async () => {
      try {
        const [summaryRes, usageRes] = await Promise.all([
          api.get<AnalyticsSummary>('/api/analytics/summary'),
          api.get<{ usage: UsageEntry[] }>('/api/analytics/usage'),
        ])
        setData(summaryRes)
        setUsage(usageRes.usage)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load analytics')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <div className="py-12 text-center text-sm text-zinc-600">Loading analytics...</div>
  if (error) return <div className="py-12 text-center text-sm text-red-400">{error}</div>
  if (!data) return null

  const maxAgentQueries = Math.max(...data.top_agents.map(a => a.query_count), 1)
  const maxDayQueries = Math.max(...data.queries_by_day.map(d => d.count), 1)

  const overviewCards = [
    { label: 'Total Queries', value: data.total_queries, accent: 'text-accent-400' },
    { label: 'Approved', value: data.total_approved, accent: 'text-emerald-400' },
    { label: 'Denied', value: data.total_denied, accent: 'text-red-400' },
    { label: 'Approval Requests', value: data.total_approval_requests, accent: 'text-amber-400' },
    { label: 'Pending', value: data.pending_approvals, accent: 'text-amber-400' },
    { label: 'Active Agents', value: data.active_agents, accent: 'text-blue-400' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Analytics</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Usage statistics and trends</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {overviewCards.map(c => (
          <div key={c.label} className="bg-zinc-900/50 rounded-xl border border-zinc-800 p-4">
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{c.label}</p>
            <p className={`text-2xl font-bold mt-1 ${c.accent}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-1 bg-zinc-900/30 rounded-xl p-1 border border-zinc-800 w-fit">
        {(['overview', 'agents', 'daily'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              tab === t ? 'bg-zinc-800 text-zinc-200' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {t === 'overview' ? 'Top Agents' : t === 'agents' ? 'Agent Breakdown' : 'Daily Volume'}
          </button>
        ))}
      </div>

      <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 p-5">
        {tab === 'overview' && (
          <>
            <h3 className="text-sm font-semibold text-zinc-100 mb-4">Top Agents by Queries</h3>
            <BarChart data={data.top_agents} labelKey="agent_id" valueKey="query_count" maxValue={maxAgentQueries} color="bg-accent-500" />
          </>
        )}
        {tab === 'agents' && (
          <>
            <h3 className="text-sm font-semibold text-zinc-100 mb-4">Agent & Tool Usage Breakdown</h3>
            {usage.length === 0 ? (
              <p className="text-sm text-zinc-500 text-center py-8">No usage data yet</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      {['Agent', 'Tool', 'Queries', 'First Used', 'Last Used'].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50">
                    {usage.map((entry, i) => (
                      <tr key={i} className="hover:bg-zinc-800/30 transition-colors">
                        <td className="px-4 py-3 text-sm font-mono text-zinc-200">{entry.agent_id}</td>
                        <td className="px-4 py-3"><span className="text-xs font-mono text-accent-400 bg-zinc-800 px-2 py-0.5 rounded">{entry.tool_name}</span></td>
                        <td className="px-4 py-3 text-sm text-zinc-300">{entry.count}</td>
                        <td className="px-4 py-3 text-xs text-zinc-500">{new Date(entry.first_used).toLocaleDateString()}</td>
                        <td className="px-4 py-3 text-xs text-zinc-500">{new Date(entry.last_used).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
        {tab === 'daily' && (
          <>
            <h3 className="text-sm font-semibold text-zinc-100 mb-4">Daily Query Volume (Last 30 Days)</h3>
            <BarChart data={data.queries_by_day} labelKey="day" valueKey="count" maxValue={maxDayQueries} color="bg-emerald-500" />
          </>
        )}
      </div>
    </div>
  )
}

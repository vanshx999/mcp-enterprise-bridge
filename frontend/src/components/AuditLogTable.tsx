import StatusBadge from './StatusBadge'

interface AuditEntry {
  id: string
  session_id: string
  agent_id: string | null
  event_type: string
  tool_name: string | null
  result_summary: string | null
  created_at: string
}

function truncate(s: string | null, len: number): string {
  if (!s) return '-'
  return s.length > len ? s.slice(0, len) + '...' : s
}

export default function AuditLogTable({ entries, onRowClick }: { entries: AuditEntry[]; onRowClick?: (e: AuditEntry) => void }) {
  if (entries.length === 0) {
    return <div className="text-center py-12 text-zinc-600 text-sm">No entries found</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full">
        <thead>
          <tr className="border-b border-zinc-800">
            {['Time', 'Agent', 'Event', 'Tool', 'Summary'].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/50">
          {entries.map((entry) => (
            <tr key={entry.id} onClick={() => onRowClick?.(entry)}
              className={`${onRowClick ? 'cursor-pointer' : ''} hover:bg-zinc-800/30 transition-colors`}>
              <td className="px-4 py-3 text-xs text-zinc-400 font-mono whitespace-nowrap">
                {new Date(entry.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </td>
              <td className="px-4 py-3 text-xs text-zinc-300 font-mono">{entry.agent_id || '-'}</td>
              <td className="px-4 py-3"><StatusBadge status={entry.event_type} /></td>
              <td className="px-4 py-3 text-xs text-zinc-400 font-mono">{entry.tool_name || '-'}</td>
              <td className="px-4 py-3 text-xs text-zinc-500 max-w-xs truncate">{truncate(entry.result_summary, 50)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface StatusBadgeProps {
  status: string
}

const variants: Record<string, string> = {
  low: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/30',
  medium: 'bg-amber-900/40 text-amber-300 border-amber-700/30',
  high: 'bg-red-900/40 text-red-300 border-red-700/30',
  pending: 'bg-amber-900/40 text-amber-300 border-amber-700/30',
  approved: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/30',
  denied: 'bg-red-900/40 text-red-300 border-red-700/30',
  timeout: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  completed: 'bg-blue-900/40 text-blue-300 border-blue-700/30',
  error: 'bg-red-900/40 text-red-300 border-red-700/30',
  permission_denied: 'bg-red-900/40 text-red-300 border-red-700/30',
  auto_approved: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/30',
  approved_and_executed: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/30',
  direct_response: 'bg-zinc-800 text-zinc-400 border-zinc-700',
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const cls = variants[status.toLowerCase()] || 'bg-zinc-800 text-zinc-400 border-zinc-700'
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${cls}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

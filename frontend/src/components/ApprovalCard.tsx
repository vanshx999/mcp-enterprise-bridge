import { useState, useEffect } from 'react'
import StatusBadge from './StatusBadge'
import { api } from '../api/client'

interface Approval {
  id: string
  session_id: string
  agent_id: string
  tool_name: string
  tool_args: Record<string, unknown>
  risk_level: string
  risk_reason: string | null
  created_at: string
  expires_at: string
}

export default function ApprovalCard({ approval }: { approval: Approval }) {
  const [timeLeft, setTimeLeft] = useState('')
  const [showApproveModal, setShowApproveModal] = useState(false)
  const [showDenyModal, setShowDenyModal] = useState(false)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const update = () => {
      const diff = new Date(approval.expires_at).getTime() - Date.now()
      if (diff <= 0) { setTimeLeft('Expired'); return }
      setTimeLeft(`${Math.floor(diff / 60000)}:${String(Math.floor((diff % 60000) / 1000)).padStart(2, '0')}`)
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [approval.expires_at])

  const handleApprove = async () => {
    setLoading(true)
    try { await api.post(`/api/approvals/${approval.id}/approve`, { note }); setShowApproveModal(false); setNote('') }
    catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
    finally { setLoading(false) }
  }

  const handleDeny = async () => {
    if (!note.trim()) return
    setLoading(true)
    try { await api.post(`/api/approvals/${approval.id}/deny`, { note }); setShowDenyModal(false); setNote('') }
    catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
    finally { setLoading(false) }
  }

  const riskBorder = approval.risk_level === 'high' ? 'border-red-800/40'
    : approval.risk_level === 'medium' ? 'border-amber-800/40'
    : 'border-emerald-800/40'

  const Modal = ({ title, onConfirm, confirmLabel, confirmColor, requireNote }: {
    title: string; onConfirm: () => void; confirmLabel: string; confirmColor: string; requireNote: boolean
  }) => (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-md w-full mx-4 shadow-2xl">
        <h3 className="text-base font-semibold text-zinc-100 mb-3">{title}</h3>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={requireNote ? 'Reason for denial (required)...' : 'Optional note...'}
          className="w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500 mb-4"
          rows={3}
        />
        <div className="flex gap-2 justify-end">
          <button onClick={() => { setShowApproveModal(false); setShowDenyModal(false); setNote('') }}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
          <button onClick={onConfirm} disabled={loading || (requireNote && !note.trim())}
            className={`px-4 py-2 text-sm font-medium rounded-lg text-white transition-opacity disabled:opacity-40 ${confirmColor}`}>
            {loading ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <>
      <div className={`bg-zinc-900/40 rounded-xl border ${riskBorder} p-5`}>
        <div className="flex items-start justify-between mb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="text-sm font-semibold text-zinc-100">{approval.agent_id}</span>
              <StatusBadge status={approval.risk_level} />
            </div>
            <p className="text-xs text-zinc-500">
              Tool: <span className="font-mono text-accent-400">{approval.tool_name}</span>
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-zinc-600 uppercase tracking-wider">Expires</p>
            <p className={`text-sm font-mono ${timeLeft === 'Expired' ? 'text-red-400' : 'text-zinc-300'}`}>{timeLeft}</p>
          </div>
        </div>

        <div className="bg-black/40 rounded-lg p-3 mb-3 font-mono text-xs text-zinc-400 overflow-x-auto max-h-32 overflow-y-auto">
          <pre>{JSON.stringify(approval.tool_args, null, 2)}</pre>
        </div>

        {approval.risk_reason && (
          <p className="text-xs text-zinc-600 mb-4">{approval.risk_reason}</p>
        )}

        <div className="flex gap-2">
          <button onClick={() => setShowApproveModal(true)}
            className="flex-1 px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors">
            Approve
          </button>
          <button onClick={() => setShowDenyModal(true)}
            className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors">
            Deny
          </button>
        </div>
      </div>

      {showApproveModal && <Modal title="Approve Request" onConfirm={handleApprove} confirmLabel="Approve" confirmColor="bg-emerald-600 hover:bg-emerald-500" requireNote={false} />}
      {showDenyModal && <Modal title="Deny Request" onConfirm={handleDeny} confirmLabel="Deny" confirmColor="bg-red-600 hover:bg-red-500" requireNote={true} />}
    </>
  )
}

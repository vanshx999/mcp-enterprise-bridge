import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import ApprovalCard from '../components/ApprovalCard'

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

export default function PendingApprovals() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [bulkAction, setBulkAction] = useState<'approve' | 'deny'>('approve')
  const [bulkNote, setBulkNote] = useState('')
  const [bulkLoading, setBulkLoading] = useState(false)

  const fetchPending = useCallback(async () => {
    try { setApprovals(await api.get<Approval[]>('/api/approvals/pending')) } catch {}
  }, [])

  const handleMessage = useCallback((data: any) => {
    if (data.type === 'new_approval') {
      setApprovals((prev) => prev.find((a) => a.id === data.data.id) ? prev : [data.data, ...prev])
    }
    if (data.type === 'approval_resolved') {
      setApprovals((prev) => { const next = prev.filter((a) => a.id !== data.data.request_id); setSelected((s) => { const n = new Set(s); n.delete(data.data.request_id); return n }); return next })
    }
  }, [])

  useWebSocket(handleMessage)
  useEffect(() => { fetchPending() }, [fetchPending])

  const toggleSelect = (id: string) => {
    setSelected((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next })
  }

  const toggleAll = () => {
    if (selected.size === approvals.length) setSelected(new Set())
    else setSelected(new Set(approvals.map((a) => a.id)))
  }

  const openBulkModal = (action: 'approve' | 'deny') => {
    setBulkAction(action)
    setBulkNote('')
    setShowBulkModal(true)
  }

  const handleBulk = async () => {
    if (bulkAction === 'deny' && !bulkNote.trim()) return
    setBulkLoading(true)
    try {
      await api.post('/api/approvals/bulk', { request_ids: Array.from(selected), action: bulkAction, note: bulkNote })
      setShowBulkModal(false); setSelected(new Set()); setBulkNote('')
    } catch (e) { alert(e instanceof Error ? e.message : 'Failed') }
    finally { setBulkLoading(false) }
  }

  const allSelected = approvals.length > 0 && selected.size === approvals.length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Pending Approvals</h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          {approvals.length > 0
            ? `${approvals.length} request${approvals.length > 1 ? 's' : ''} waiting for your review`
            : 'All caught up — no pending requests'}
        </p>
      </div>

      {approvals.length === 0 ? (
        <div className="bg-zinc-900/30 rounded-xl border border-zinc-800 py-16 text-center">
          <div className="text-4xl mb-3 opacity-30">&#10003;</div>
          <p className="text-zinc-600 text-sm">No pending approvals</p>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm text-zinc-400 cursor-pointer">
              <input type="checkbox" checked={allSelected} onChange={toggleAll}
                className="rounded border-zinc-700 bg-zinc-800 text-accent-500 focus:ring-accent-500" />
              Select all ({approvals.length})
            </label>
            {selected.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-500">{selected.size} selected</span>
                <button onClick={() => openBulkModal('approve')}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors">
                  Bulk Approve
                </button>
                <button onClick={() => openBulkModal('deny')}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs font-medium rounded-lg transition-colors">
                  Bulk Deny
                </button>
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {approvals.map((a) => (
              <div key={a.id} className="relative">
                <div className="absolute top-3 left-3 z-10">
                  <input type="checkbox" checked={selected.has(a.id)} onChange={() => toggleSelect(a.id)}
                    className="rounded border-zinc-700 bg-zinc-800 text-accent-500 focus:ring-accent-500" />
                </div>
                <div className="pl-8">
                  <ApprovalCard approval={a} />
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {showBulkModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-base font-semibold text-zinc-100 mb-1">
              {bulkAction === 'approve' ? 'Bulk Approve' : 'Bulk Deny'} ({selected.size} requests)
            </h3>
            <p className="text-xs text-zinc-500 mb-4">
              This will {bulkAction === 'approve' ? 'approve' : 'deny'} all {selected.size} selected request{selected.size > 1 ? 's' : ''}.
            </p>
            <textarea
              value={bulkNote}
              onChange={(e) => setBulkNote(e.target.value)}
              placeholder={bulkAction === 'deny' ? 'Reason for denial (required)...' : 'Optional note...'}
              className="w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent-500 mb-4"
              rows={3}
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowBulkModal(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Cancel</button>
              <button onClick={handleBulk} disabled={bulkLoading || (bulkAction === 'deny' && !bulkNote.trim())}
                className={`px-4 py-2 text-sm font-medium rounded-lg text-white transition-opacity disabled:opacity-40 ${bulkAction === 'approve' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-red-600 hover:bg-red-500'}`}>
                {bulkLoading ? 'Processing...' : bulkAction === 'approve' ? 'Bulk Approve' : 'Bulk Deny'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

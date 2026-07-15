import { useEffect, useCallback } from 'react'
import { useToastStore } from '../store/toastStore'
import { useWebSocket } from '../hooks/useWebSocket'

const typeStyles: Record<string, string> = {
  info: 'border-accent-500/40 bg-accent-500/10',
  success: 'border-emerald-500/40 bg-emerald-500/10',
  warning: 'border-amber-500/40 bg-amber-500/10',
  error: 'border-red-500/40 bg-red-500/10',
}

export default function ToastContainer() {
  const { toasts, removeToast } = useToastStore()

  const handleMessage = useCallback((data: any) => {
    if (data.type === 'new_approval') {
      useToastStore.getState().addToast({
        type: 'warning',
        message: `New approval request from "${data.data?.agent_id || 'unknown'}" — ${data.data?.tool_name || 'unknown tool'}`,
      })
    }
    if (data.type === 'approval_resolved') {
      useToastStore.getState().addToast({
        type: 'info',
        message: `Approval request resolved`,
      })
    }
  }, [])

  useWebSocket(handleMessage)

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`border rounded-lg px-4 py-3 text-sm shadow-lg backdrop-blur-sm flex items-start gap-2 ${typeStyles[t.type] || typeStyles.info}`}
        >
          <span className="text-zinc-200 flex-1">{t.message}</span>
          <button onClick={() => removeToast(t.id)} className="text-zinc-500 hover:text-zinc-300 transition-colors shrink-0">✕</button>
        </div>
      ))}
    </div>
  )
}

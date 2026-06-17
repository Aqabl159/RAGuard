import { AlertTriangle, X } from 'lucide-react'
import { useState } from 'react'
import type { ConflictWarning as ConflictWarningType } from '../../types'

interface Props {
  warning: ConflictWarningType | null
}

export default function ConflictWarning({ warning }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (!warning || !warning.has_conflict) return null

  return (
    <div className="mt-3 rounded-lg border border-red-200 bg-red-50 overflow-hidden">
      {/* Banner */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-red-100/50 transition-colors"
      >
        <AlertTriangle size={16} className="text-red-500 shrink-0" />
        <span className="text-sm font-medium text-red-700 flex-1">
          检测到信息冲突
        </span>
        <span className="text-xs text-red-400">
          {warning.conflict_ids.length} 个冲突 {expanded ? '▴' : '▾'}
        </span>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-3 border-t border-red-200">
          <p className="text-xs text-red-600 mt-2 whitespace-pre-wrap leading-relaxed">
            {warning.description}
          </p>
          {warning.conflicting_chunks.length > 0 && (
            <div className="mt-2 space-y-1.5">
              {warning.conflicting_chunks.map((chunk: Record<string, unknown>, i: number) => (
                <div key={i} className="text-xs bg-white/60 rounded px-2.5 py-1.5 text-red-700">
                  <span className="font-medium">
                    [{chunk.role === 'source_a' ? '来源A' : '来源B'}]
                  </span>{' '}
                  {chunk.claim as string}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

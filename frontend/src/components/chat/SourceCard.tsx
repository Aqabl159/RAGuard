import { useState } from 'react'
import { FileText, ChevronDown } from 'lucide-react'
import type { SourceInfo } from '../../types'

interface Props {
  sources: SourceInfo[]
}

export default function SourceCard({ sources }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-3 border border-slate-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-slate-50 transition-colors"
      >
        <FileText size={14} className="text-slate-400" />
        <span className="text-xs font-medium text-slate-500">
          参考来源 ({sources.length})
        </span>
        <ChevronDown
          size={14}
          className={`text-slate-400 ml-auto transition-transform ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {expanded && (
        <div className="border-t border-slate-200 divide-y divide-slate-100">
          {sources.map((s, i) => (
            <div key={i} className="px-3 py-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-slate-600 truncate max-w-[70%]">
                  {s.document_title || '未知文档'}
                </span>
                <span className="text-xs text-slate-400">
                  相关度: {(s.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-xs text-slate-500 line-clamp-3 leading-relaxed">
                {s.content}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

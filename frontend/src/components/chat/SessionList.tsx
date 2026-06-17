import { Plus, Trash2, MessageSquare, Loader2 } from 'lucide-react'
import type { QASession } from '../../types'

interface Props {
  sessions: QASession[]
  activeId: string | null
  loading: boolean
  onSelect: (id: string) => void
  onCreate: () => void
  onDelete: (id: string) => void
}

export default function SessionList({ sessions, activeId, loading, onSelect, onCreate, onDelete }: Props) {
  return (
    <div className="w-64 border-r border-slate-200 bg-white flex flex-col shrink-0">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-600">对话历史</h3>
        <button
          onClick={onCreate}
          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          title="新建对话"
        >
          <Plus size={16} />
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={18} className="animate-spin text-slate-300" />
          </div>
        ) : sessions.length === 0 ? (
          <p className="text-xs text-slate-400 text-center py-8 px-4">
            暂无对话，点击 + 开始提问
          </p>
        ) : (
          sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelect(session.id)}
              className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-left text-sm transition-colors group ${
                activeId === session.id
                  ? 'bg-indigo-50 text-indigo-700 border-r-2 border-indigo-500'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <MessageSquare size={14} className="shrink-0 opacity-50" />
              <span className="flex-1 truncate text-xs">{session.title || '新对话'}</span>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(session.id) }}
                className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-400 hover:text-red-500 transition-all"
                title="删除"
              >
                <Trash2 size={12} />
              </button>
            </button>
          ))
        )}
      </div>
    </div>
  )
}

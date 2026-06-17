import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiRequest } from '../api/client'
import type { RepairAction, PaginatedResponse } from '../types'
import { History, Check, X, Trash2, FileEdit, Plus, Loader2, ChevronDown, ChevronUp } from 'lucide-react'

const actionIcons: Record<string, typeof Check> = {
  create_chunk: Plus,
  update_chunk: FileEdit,
  delete_chunk: Trash2,
  merge_chunks: FileEdit,
}

const actionLabels: Record<string, string> = {
  create_chunk: '创建分块',
  update_chunk: '更新分块',
  delete_chunk: '删除分块',
  merge_chunks: '合并分块',
}

export default function AuditPage() {
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['repair-actions', page],
    queryFn: () => apiRequest<PaginatedResponse<RepairAction>>('/repair-actions', {
      params: { page, per_page: 30 },
    }),
  })

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">审计日志</h1>
        <p className="text-sm text-slate-500 mt-1">知识库修复操作的完整追溯记录</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-slate-300" />
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-slate-200">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
            <History size={28} className="text-slate-300" />
          </div>
          <h3 className="text-lg font-medium text-slate-500 mb-1">暂无审计记录</h3>
          <p className="text-sm text-slate-400">当消解方案被批准并执行修复后，记录将显示在这里</p>
        </div>
      ) : (
        <>
          {/* Timeline */}
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-5 top-0 bottom-0 w-px bg-slate-200" />

            <div className="space-y-3">
              {data.items.map((action) => {
                const isExpanded = expandedId === action.id
                const Icon = actionIcons[action.action_type] || FileEdit

                return (
                  <div key={action.id} className="relative pl-12">
                    {/* Dot */}
                    <div className={`absolute left-3.5 w-3 h-3 rounded-full border-2 border-white ${
                      action.success ? 'bg-green-400' : 'bg-red-400'
                    } ring-2 ${action.success ? 'ring-green-200' : 'ring-red-200'}`} />

                    {/* Card */}
                    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:border-slate-300 transition-colors">
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : action.id)}
                        className="w-full px-4 py-3 flex items-center gap-3 text-left"
                      >
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          action.success ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'
                        }`}>
                          <Icon size={16} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-slate-700">
                              {actionLabels[action.action_type] || action.action_type}
                            </span>
                            {action.success ? (
                              <Check size={14} className="text-green-400" />
                            ) : (
                              <X size={14} className="text-red-400" />
                            )}
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5">
                            {action.executed_at ? new Date(action.executed_at).toLocaleString('zh-CN') : ''}
                            {action.chunk_id && <span className="ml-2 font-mono">ID: {action.chunk_id.slice(0, 8)}...</span>}
                          </p>
                        </div>
                        {isExpanded ? <ChevronUp size={16} className="text-slate-400 shrink-0" /> :
                                      <ChevronDown size={16} className="text-slate-400 shrink-0" />}
                      </button>

                      {/* Expanded diff view */}
                      {isExpanded && (action.old_content || action.new_content) && (
                        <div className="border-t border-slate-100 px-4 py-3 space-y-3">
                          {action.old_content && (
                            <div>
                              <p className="text-xs font-medium text-red-500 mb-1">— 原内容</p>
                              <pre className="text-xs text-slate-600 bg-red-50 rounded-lg p-2.5 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                {action.old_content}
                              </pre>
                            </div>
                          )}
                          {action.new_content && (
                            <div>
                              <p className="text-xs font-medium text-green-500 mb-1">+ 新内容</p>
                              <pre className="text-xs text-slate-600 bg-green-50 rounded-lg p-2.5 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                {action.new_content}
                              </pre>
                            </div>
                          )}
                          {action.error_message && (
                            <div className="p-2 bg-red-50 rounded-lg text-xs text-red-600">
                              错误: {action.error_message}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              {Array.from({ length: data.pages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                    p === page
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

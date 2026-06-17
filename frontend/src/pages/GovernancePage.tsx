import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '../api/client'
import type { ConflictStats, Conflict, Resolution, PaginatedResponse } from '../types'
import {
  Shield, AlertTriangle, CheckCircle, Clock, Loader2,
  ChevronDown, ChevronUp, Check, X, Edit3, ArrowRight
} from 'lucide-react'

export default function GovernancePage() {
  const queryClient = useQueryClient()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [pendingResolveId, setPendingResolveId] = useState<string | null>(null)
  const [modifyContent, setModifyContent] = useState('')
  const [modifyAction, setModifyAction] = useState('')
  const [modifyId, setModifyId] = useState<string | null>(null)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['conflict-stats'],
    queryFn: () => apiRequest<ConflictStats>('/conflicts/stats'),
  })

  const { data: conflictsData, isLoading: conflictsLoading } = useQuery({
    queryKey: ['conflicts'],
    queryFn: () => apiRequest<PaginatedResponse<Conflict>>('/conflicts', {
      params: { status: 'open', page: 1, per_page: 20 },
    }),
  })

  // Fetch pending resolutions
  const { data: pendingData } = useQuery({
    queryKey: ['pending-resolutions'],
    queryFn: () => apiRequest<{ items: { resolution: Resolution; conflict: Conflict }[] }>('/governance/pending'),
  })

  const resolveMutation = useMutation({
    mutationFn: (conflictId: string) =>
      apiRequest<{ resolution_id: string; status: string; resolution: Resolution }>(`/conflicts/${conflictId}/resolve`, { method: 'POST' }),
    onSuccess: (data) => {
      setPendingResolveId(null)
      if (data?.resolution) {
        // Add the new resolution to the pending-resolutions cache immediately
        queryClient.setQueryData(['pending-resolutions'], (old: { items: { resolution: Resolution; conflict: Conflict }[] } | undefined) => {
          const newItem = { resolution: data.resolution!, conflict: undefined } as { resolution: Resolution; conflict: Conflict }
          return { items: [...(old?.items || []), newItem] }
        })
      }
      queryClient.invalidateQueries({ queryKey: ['conflicts'] })
      queryClient.invalidateQueries({ queryKey: ['pending-resolutions'] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: (resolutionId: string) => apiRequest(`/resolutions/${resolutionId}/approve`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conflicts'] })
      queryClient.invalidateQueries({ queryKey: ['pending-resolutions'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (resolutionId: string) => apiRequest(`/resolutions/${resolutionId}/reject`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conflicts'] })
      queryClient.invalidateQueries({ queryKey: ['pending-resolutions'] })
    },
  })

  const modifyMutation = useMutation({
    mutationFn: ({ id, content, action }: { id: string; content: string; action?: string }) =>
      apiRequest(`/resolutions/${id}/modify`, {
        method: 'POST',
        body: { modified_content: content, modified_action: action || undefined },
      }),
    onSuccess: () => {
      setModifyId(null)
      setModifyContent('')
      setModifyAction('')
      queryClient.invalidateQueries({ queryKey: ['pending-resolutions'] })
    },
  })

  // Find pending resolution for a conflict
  const getPendingResolution = (conflictId: string) => {
    if (!pendingData?.items) return null
    const found = pendingData.items.find(
      (item) => item.resolution.conflict_id === conflictId && item.resolution.status === 'pending_review'
    )
    return found?.resolution ?? null
  }

  const actionLabels: Record<string, string> = {
    replace_both: '替换双方',
    keep_a_remove_b: '保留A删除B',
    keep_b_remove_a: '保留B删除A',
    merge: '合并',
    manual_rewrite: '人工重写',
  }

  if (statsLoading || conflictsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={24} className="animate-spin text-slate-300" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">冲突治理</h1>
        <p className="text-sm text-slate-500 mt-1">审核和消解知识库中的信息冲突</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard icon={AlertTriangle} label="未处理" value={stats?.by_status?.open ?? 0} color="red" />
        <StatCard icon={Clock} label="审核中" value={stats?.by_status?.in_review ?? 0} color="amber" />
        <StatCard icon={CheckCircle} label="已解决" value={stats?.by_status?.resolved ?? 0} color="green" />
        <StatCard icon={Shield} label="总计" value={stats?.total ?? 0} color="indigo" />
      </div>

      {/* Conflict List */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50">
          <h3 className="text-sm font-semibold text-slate-600">冲突列表</h3>
        </div>
        {conflictsData?.items.length === 0 ? (
          <div className="text-center py-16 text-slate-400">
            <CheckCircle size={32} className="mx-auto mb-3 text-green-300" />
            <p className="text-sm">暂无冲突，知识库一致</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {conflictsData?.items.map((conflict) => {
              const isExpanded = expandedId === conflict.id
              const pendingResolution = getPendingResolution(conflict.id)

              return (
                <div key={conflict.id} className="hover:bg-slate-50/30 transition-colors">
                  {/* Card header */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : conflict.id)}
                    className="w-full px-5 py-4 flex items-start gap-3 text-left"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <SeverityBadge severity={conflict.severity} />
                        <StatusBadge status={conflict.status} />
                        <TypeBadge type={conflict.conflict_type} />
                      </div>
                      <p className="text-sm font-medium text-slate-700">{conflict.summary}</p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {conflict.source_a?.document_title || '文档A'}
                        <ArrowRight size={10} className="inline mx-1" />
                        {conflict.source_b?.document_title || '文档B'}
                        {' · '}{conflict.detected_at ? new Date(conflict.detected_at).toLocaleDateString('zh-CN') : ''}
                      </p>
                    </div>
                    {isExpanded ? <ChevronUp size={18} className="text-slate-400 shrink-0 mt-1" /> :
                                  <ChevronDown size={18} className="text-slate-400 shrink-0 mt-1" />}
                  </button>

                  {/* Expanded detail */}
                  {isExpanded && (
                    <div className="px-5 pb-5 border-t border-slate-100 pt-4">
                      {/* Chunk Comparison */}
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <ChunkView
                          label="来源 A"
                          docTitle={conflict.source_a?.document_title}
                          content={conflict.source_a?.content}
                          claim={conflict.source_a?.claim}
                          color="blue"
                        />
                        <ChunkView
                          label="来源 B"
                          docTitle={conflict.source_b?.document_title}
                          content={conflict.source_b?.content}
                          claim={conflict.source_b?.claim}
                          color="amber"
                        />
                      </div>

                      {/* LLM Analysis */}
                      {conflict.description && (
                        <div className="mb-4 p-3 bg-slate-50 rounded-lg">
                          <p className="text-xs font-medium text-slate-500 mb-1">AI 分析</p>
                          <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                            {conflict.description}
                          </p>
                        </div>
                      )}

                      {/* Resolution Section */}
                      <div className="border-t border-slate-100 pt-4">
                        {!pendingResolution && pendingResolveId !== conflict.id && (
                          <button
                            onClick={() => {
                              setPendingResolveId(conflict.id)
                              resolveMutation.mutate(conflict.id)
                            }}
                            disabled={resolveMutation.isPending}
                            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                          >
                            {resolveMutation.isPending ? '生成中...' : '生成消解方案'}
                          </button>
                        )}

                        {pendingResolveId === conflict.id && resolveMutation.isPending && (
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <Loader2 size={16} className="animate-spin" />
                            正在生成消解方案，请稍候...
                          </div>
                        )}

                        {/* Pending Resolution Actions */}
                        {pendingResolution && (
                          <div>
                            <div className="flex items-center gap-2 mb-3">
                              <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                                建议: {actionLabels[pendingResolution.proposed_action] || pendingResolution.proposed_action}
                              </span>
                            </div>

                            {/* Proposed content */}
                            {pendingResolution.proposed_content && (
                              <div className="mb-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                                <p className="text-xs font-medium text-green-700 mb-1">建议内容</p>
                                <p className="text-sm text-green-800 whitespace-pre-wrap">
                                  {pendingResolution.proposed_content}
                                </p>
                              </div>
                            )}

                            {/* Reasoning */}
                            <div className="mb-4 p-3 bg-slate-50 rounded-lg">
                              <p className="text-xs font-medium text-slate-500 mb-1">推理过程</p>
                              <p className="text-sm text-slate-600">{pendingResolution.reasoning}</p>
                            </div>

                            {/* Modify editor */}
                            {modifyId === pendingResolution.id && (
                              <div className="mb-4 space-y-3">
                                {/* Action type selector */}
                                <div>
                                  <p className="text-xs font-medium text-slate-500 mb-1.5">消解动作</p>
                                  <div className="grid grid-cols-2 gap-2">
                                    {Object.entries(actionLabels).map(([value, label]) => (
                                      <button
                                        key={value}
                                        onClick={() => setModifyAction(value)}
                                        className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors text-left ${
                                          modifyAction === value
                                            ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                                            : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                                        }`}
                                      >
                                        {label}
                                      </button>
                                    ))}
                                  </div>
                                </div>
                                {/* Content textarea */}
                                <div>
                                  <p className="text-xs font-medium text-slate-500 mb-1.5">修改内容</p>
                                  <textarea
                                    value={modifyContent}
                                    onChange={(e) => setModifyContent(e.target.value)}
                                    rows={4}
                                    placeholder="输入修改后的内容..."
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                                  />
                                </div>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => modifyMutation.mutate({
                                      id: pendingResolution.id,
                                      content: modifyContent,
                                      action: modifyAction,
                                    })}
                                    disabled={!modifyContent.trim() || modifyMutation.isPending}
                                    className="px-3 py-1.5 bg-purple-600 text-white text-xs font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50"
                                  >
                                    提交修改
                                  </button>
                                  <button
                                    onClick={() => { setModifyId(null); setModifyContent(''); setModifyAction('') }}
                                    className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700"
                                  >
                                    取消
                                  </button>
                                </div>
                              </div>
                            )}

                            {/* Action buttons */}
                            {modifyId !== pendingResolution.id && (
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => approveMutation.mutate(pendingResolution.id)}
                                  disabled={approveMutation.isPending}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                                >
                                  <Check size={14} /> 批准并修复
                                </button>
                                <button
                                  onClick={() => rejectMutation.mutate(pendingResolution.id)}
                                  disabled={rejectMutation.isPending}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-red-100 text-red-700 text-xs font-medium rounded-lg hover:bg-red-200 disabled:opacity-50 transition-colors"
                                >
                                  <X size={14} /> 拒绝
                                </button>
                                <button
                                  onClick={() => {
                                    setModifyId(pendingResolution.id)
                                    setModifyContent(pendingResolution.proposed_content || '')
                                    setModifyAction(pendingResolution.proposed_action || '')
                                  }}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-700 text-xs font-medium rounded-lg hover:bg-slate-200 transition-colors"
                                >
                                  <Edit3 size={14} /> 修改
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ---- Sub Components ----

function StatCard({ icon: Icon, label, value, color }: {
  icon: typeof AlertTriangle; label: string; value: number; color: string
}) {
  const colors: Record<string, string> = {
    red: 'bg-red-50 text-red-600', amber: 'bg-amber-50 text-amber-600',
    green: 'bg-green-50 text-green-600', indigo: 'bg-indigo-50 text-indigo-600',
  }
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
        <Icon size={20} />
      </div>
      <div><p className="text-xs text-slate-400">{label}</p>
        <p className="text-2xl font-bold text-slate-700">{value}</p></div>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    critical: 'bg-red-600 text-white', high: 'bg-orange-500 text-white',
    medium: 'bg-amber-500 text-white', low: 'bg-blue-400 text-white',
  }
  const labels: Record<string, string> = { critical: '严重', high: '高', medium: '中', low: '低' }
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${map[severity] || 'bg-gray-100'}`}>{labels[severity] || severity}</span>
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    open: 'bg-red-50 text-red-600', in_review: 'bg-amber-50 text-amber-600',
    resolved: 'bg-green-50 text-green-600', dismissed: 'bg-gray-50 text-gray-500',
  }
  const labels: Record<string, string> = { open: '未处理', in_review: '审核中', resolved: '已解决', dismissed: '已忽略' }
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${map[status] || ''}`}>{labels[status] || status}</span>
}

function TypeBadge({ type }: { type: string }) {
  const labels: Record<string, string> = {
    factual_contradiction: '事实矛盾', numerical_discrepancy: '数值不一致',
    temporal_conflict: '时效冲突', definition_mismatch: '定义不匹配',
    conditional_vs_absolute: '条件vs绝对',
  }
  return <span className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-500">{labels[type] || type}</span>
}

function ChunkView({ label, docTitle, content, claim, color }: {
  label: string; docTitle?: string; content?: string; claim?: string; color: string
}) {
  const borders: Record<string, string> = { blue: 'border-l-blue-400', amber: 'border-l-amber-400' }
  return (
    <div className={`border-l-4 ${borders[color] || 'border-l-slate-300'} bg-slate-50 rounded-r-lg p-3`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500">{label}</span>
        <span className="text-xs text-slate-400 truncate max-w-[60%]">{docTitle || '未知文档'}</span>
      </div>
      <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap max-h-36 overflow-y-auto">
        {content || '(无内容)'}
      </p>
      {claim && (
        <div className="mt-2 pt-2 border-t border-slate-200">
          <span className="text-xs text-indigo-500 font-medium">主张: </span>
          <span className="text-xs text-slate-600">{claim}</span>
        </div>
      )}
    </div>
  )
}

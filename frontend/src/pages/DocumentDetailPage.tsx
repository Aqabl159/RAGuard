import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiRequest } from '../api/client'
import type { Document, Chunk, PaginatedResponse } from '../types'
import { ArrowLeft, Loader2, File, FileText } from 'lucide-react'

export default function DocumentDetailPage() {
  const { docId } = useParams<{ docId: string }>()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const perPage = 20

  const { data: doc, isLoading: docLoading } = useQuery({
    queryKey: ['document', docId],
    queryFn: () => apiRequest<Document>(`/documents/${docId}`),
    enabled: !!docId,
  })

  const { data: chunksData, isLoading: chunksLoading } = useQuery({
    queryKey: ['document-chunks', docId, page],
    queryFn: () =>
      apiRequest<PaginatedResponse<Chunk>>(`/documents/${docId}/chunks`, {
        params: { page, per_page: perPage },
      }),
    enabled: !!docId,
  })

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      pending: 'bg-amber-100 text-amber-700',
      processing: 'bg-blue-100 text-blue-700',
      indexed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
    }
    const labels: Record<string, string> = {
      pending: '待处理', processing: '处理中', indexed: '已索引', failed: '失败',
    }
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[status] || 'bg-gray-100 text-gray-500'}`}>
        {labels[status] || status}
      </span>
    )
  }

  if (docLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={24} className="animate-spin text-slate-300" />
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-center py-20">
        <p className="text-slate-500">文档不存在或已删除</p>
        <button
          onClick={() => navigate('/documents')}
          className="mt-4 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
        >
          返回文档列表
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/documents')}
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-3 transition-colors"
        >
          <ArrowLeft size={16} />
          返回文档列表
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              {doc.title || doc.filename}
            </h1>
            <p className="text-sm text-slate-400 mt-1">{doc.filename}</p>
          </div>
          <div className="flex items-center gap-2">
            {statusBadge(doc.status)}
          </div>
        </div>
      </div>

      {/* Metadata Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetaCard label="类型" value={doc.doc_type.toUpperCase()} />
        <MetaCard label="大小" value={formatSize(doc.file_size)} />
        <MetaCard label="分块数" value={String(doc.chunk_count ?? '-')} />
        <MetaCard label="冲突数" value={String(doc.conflict_count ?? 0)} />
      </div>

      {/* Chunks */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-600">
            分块列表
            {chunksData && <span className="text-slate-400 ml-1">({chunksData.total})</span>}
          </h3>
        </div>

        {chunksLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={20} className="animate-spin text-slate-300" />
          </div>
        ) : !chunksData || chunksData.items.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <p className="text-sm">暂无分块数据</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {chunksData.items.map((chunk) => (
              <div key={chunk.id} className="px-5 py-3 hover:bg-slate-50/30 transition-colors">
                <div className="flex items-center gap-3 mb-2">
                  <span className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-600 text-xs font-bold flex items-center justify-center shrink-0">
                    {chunk.chunk_index}
                  </span>
                  <span className="text-xs text-slate-400">
                    {chunk.token_count ? `${chunk.token_count} tokens` : ''}
                    {chunk.page_number ? ` · 第${chunk.page_number}页` : ''}
                  </span>
                  {!chunk.is_active && (
                    <span className="px-1.5 py-0.5 rounded text-xs bg-red-50 text-red-500">已停用</span>
                  )}
                </div>
                <pre className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap font-sans">
                  {chunk.content}
                </pre>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {chunksData && chunksData.pages > 1 && (
          <div className="flex items-center justify-center gap-2 px-5 py-3 border-t border-slate-100">
            {Array.from({ length: chunksData.pages }, (_, i) => i + 1).map((p) => (
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
      </div>
    </div>
  )
}

function MetaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-lg font-bold text-slate-700">{value}</p>
    </div>
  )
}

function formatSize(bytes?: number): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

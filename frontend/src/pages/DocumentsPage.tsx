import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest, createFormData } from '../api/client'
import type { Document, PaginatedResponse } from '../types'
import { Upload, FileText, File, FolderOpen, Trash2, Loader2, AlertCircle } from 'lucide-react'

export default function DocumentsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => apiRequest<PaginatedResponse<Document>>('/documents'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiRequest(`/documents/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    setError(null)
    try {
      await apiRequest('/documents/upload', {
        method: 'POST',
        body: createFormData(Array.from(files)),
      })
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      pending: 'bg-amber-100 text-amber-700',
      processing: 'bg-blue-100 text-blue-700',
      indexed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
    }
    const labels: Record<string, string> = {
      pending: '待处理',
      processing: '处理中',
      indexed: '已索引',
      failed: '失败',
    }
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[status] || 'bg-gray-100 text-gray-500'}`}>
        {labels[status] || status}
      </span>
    )
  }

  const typeIcon = (docType: string) => {
    if (docType === 'pdf') return <File size={18} className="text-red-400" />
    if (docType === 'docx') return <FileText size={18} className="text-blue-400" />
    return <FileText size={18} className="text-emerald-400" />
  }

  const formatSize = (bytes?: number) => {
    if (!bytes) return '-'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">文档管理</h1>
          <p className="text-sm text-slate-500 mt-1">上传和管理知识库文档</p>
        </div>
        <label className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg cursor-pointer transition-colors">
          <Upload size={16} />
          {uploading ? '上传中...' : '上传文档'}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.md"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Document list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-slate-300" />
        </div>
      ) : data?.items.length === 0 ? (
        <div className="text-center py-20">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
            <FolderOpen size={28} className="text-slate-300" />
          </div>
          <h3 className="text-lg font-medium text-slate-500 mb-1">暂无文档</h3>
          <p className="text-sm text-slate-400">上传 PDF、DOCX 或 Markdown 文件开始构建知识库</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">文档</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">类型</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">大小</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">分块</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">冲突</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">状态</th>
                <th className="text-right px-5 py-3 text-xs font-semibold text-slate-400 uppercase">操作</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((doc) => (
                <tr
                  key={doc.id}
                  className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors cursor-pointer"
                  onClick={() => navigate(`/documents/${doc.id}`)}
                >
                  <td className="px-5 py-3">
                    <span className="text-sm font-medium text-slate-700 truncate block max-w-60">
                      {doc.title || doc.filename}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
                      {typeIcon(doc.doc_type)}
                      {doc.doc_type.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-sm text-slate-500">{formatSize(doc.file_size)}</td>
                  <td className="px-5 py-3 text-sm text-slate-500">{doc.chunk_count ?? '-'}</td>
                  <td className="px-5 py-3">
                    {(doc.conflict_count ?? 0) > 0 ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-600">
                        {doc.conflict_count}
                      </span>
                    ) : (
                      <span className="text-sm text-slate-400">0</span>
                    )}
                  </td>
                  <td className="px-5 py-3">{statusBadge(doc.status)}</td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(doc.id) }}
                      disabled={deleteMutation.isPending}
                      className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                      title="删除文档"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.total > 0 && (
        <p className="text-xs text-slate-400 mt-3">共 {data.total} 份文档</p>
      )}
    </div>
  )
}

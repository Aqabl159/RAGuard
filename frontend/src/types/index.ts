export interface Document {
  id: string
  filename: string
  title?: string
  doc_type: 'pdf' | 'docx' | 'markdown'
  status: 'pending' | 'processing' | 'indexed' | 'failed' | 'deleted'
  page_count?: number
  file_size?: number
  chunk_count?: number
  conflict_count?: number
  error_message?: string
  created_at?: string
  updated_at?: string
}

export interface Chunk {
  id: string
  document_id: string
  content: string
  chunk_index: number
  page_number?: number
  token_count?: number
  is_active: boolean
  created_at?: string
}

export interface Conflict {
  id: string
  scan_job_id?: string
  conflict_type: string
  summary: string
  description?: string
  status: 'open' | 'in_review' | 'resolved' | 'dismissed'
  severity: 'low' | 'medium' | 'high' | 'critical'
  detection_method: string
  detected_at?: string
  resolved_at?: string
  source_a?: ConflictChunkInfo
  source_b?: ConflictChunkInfo
}

export interface ConflictChunkInfo {
  chunk_id: string
  document_id: string
  document_title?: string
  content: string
  claim: string
  role: 'source_a' | 'source_b'
  similarity_score?: number
}

export interface ScanJob {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  total_pairs: number
  conflict_pairs: number
  conflicts_found: number
  threshold: number
  started_at?: string
  completed_at?: string
  created_at?: string
  error_message?: string
}

export interface Resolution {
  id: string
  conflict_id: string
  graph_thread_id?: string
  proposed_action: string
  proposed_content?: string
  reasoning: string
  status: string
  human_decision?: string
  human_notes?: string
  human_modified_content?: string
  created_at?: string
  reviewed_at?: string
  applied_at?: string
}

export interface RepairAction {
  id: string
  resolution_id: string
  action_type: string
  chunk_id?: string
  old_content?: string
  new_content?: string
  executed_at?: string
  success: boolean
  error_message?: string
}

export interface QASession {
  id: string
  title?: string
  created_at?: string
  updated_at?: string
  message_count?: number
}

export interface QAMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  conflict_warning?: ConflictWarning
  tokens_used?: number
  latency_ms?: number
  created_at?: string
}

export interface SourceInfo {
  chunk_id: string
  document_id: string
  document_title?: string
  content: string
  score: number
}

export interface ConflictWarning {
  has_conflict: boolean
  conflict_ids: string[]
  description?: string
  conflicting_chunks: Record<string, unknown>[]
}

export interface ConflictStats {
  total: number
  by_status: Record<string, number>
  by_severity: Record<string, number>
  by_type: Record<string, number>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pages: number
}

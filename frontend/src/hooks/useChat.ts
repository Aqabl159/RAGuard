import { useState, useCallback, useEffect } from 'react'
import { apiRequest } from '../api/client'
import type { QASession, QAMessage } from '../types'

export function useChat() {
  const [sessions, setSessions] = useState<QASession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<QAMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [sessionsLoading, setSessionsLoading] = useState(false)

  // Load sessions
  const loadSessions = useCallback(async () => {
    setSessionsLoading(true)
    try {
      const data = await apiRequest<{ items: QASession[]; total: number }>('/qa/sessions')
      setSessions(data.items)
    } catch { /* ignore */ }
    finally { setSessionsLoading(false) }
  }, [])

  useEffect(() => { loadSessions() }, [loadSessions])

  // Create a new session
  const createSession = useCallback(async () => {
    const session = await apiRequest<QASession>('/qa/sessions', {
      method: 'POST', body: { title: '新对话' },
    })
    setSessions(prev => [session, ...prev])
    setActiveSessionId(session.id)
    setMessages([])
    return session.id
  }, [])

  // Load messages for a session
  const loadSession = useCallback(async (sessionId: string) => {
    setActiveSessionId(sessionId)
    try {
      const data = await apiRequest<{ session: QASession; messages: QAMessage[] }>(
        `/qa/sessions/${sessionId}?messages_limit=50`
      )
      setMessages(data.messages || [])
    } catch { setMessages([]) }
  }, [])

  // Send a message
  const sendMessage = useCallback(async (content: string) => {
    let sessionId = activeSessionId
    if (!sessionId) {
      sessionId = await createSession()
    }

    // Optimistic user message
    const userMsg: QAMessage = {
      id: `temp-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const data = await apiRequest<{
        message: QAMessage
        answer: { content: string; sources: unknown[]; conflict_warning?: unknown }
      }>(`/qa/sessions/${sessionId}/messages`, {
        method: 'POST',
        body: { content },
      })

      setMessages(prev => prev.filter(m => m.id !== userMsg.id).concat([
        {
          id: `u-${Date.now()}`,
          session_id: sessionId,
          role: 'user',
          content,
          created_at: new Date().toISOString(),
        },
        data.message,
      ]))
    } catch (err) {
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        session_id: sessionId,
        role: 'assistant',
        content: `发送失败：${err instanceof Error ? err.message : '未知错误'}`,
        created_at: new Date().toISOString(),
      }])
    } finally {
      setLoading(false)
    }
  }, [activeSessionId, createSession])

  // Delete a session
  const deleteSession = useCallback(async (sessionId: string) => {
    await apiRequest(`/qa/sessions/${sessionId}`, { method: 'DELETE' })
    setSessions(prev => prev.filter(s => s.id !== sessionId))
    if (activeSessionId === sessionId) {
      setActiveSessionId(null)
      setMessages([])
    }
  }, [activeSessionId])

  return {
    sessions, sessionsLoading,
    activeSessionId, messages, loading,
    createSession, loadSession, sendMessage, deleteSession,
  }
}

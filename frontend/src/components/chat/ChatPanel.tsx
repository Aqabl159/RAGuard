import { useEffect, useRef } from 'react'
import { useChat } from '../../hooks/useChat'
import SessionList from './SessionList'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import { Loader2, MessageSquare } from 'lucide-react'

export default function ChatPanel() {
  const {
    sessions, sessionsLoading,
    activeSessionId, messages, loading,
    createSession, loadSession, sendMessage, deleteSession,
  } = useChat()

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="h-full flex">
      {/* Left sidebar - Session list */}
      <SessionList
        sessions={sessions}
        activeId={activeSessionId}
        loading={sessionsLoading}
        onSelect={loadSession}
        onCreate={createSession}
        onDelete={deleteSession}
      />

      {/* Right - Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {!activeSessionId ? (
          /* Empty state */
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-5 rounded-2xl bg-indigo-100 flex items-center justify-center">
                <MessageSquare size={36} className="text-indigo-500" />
              </div>
              <h2 className="text-xl font-semibold text-slate-700 mb-2">RAGuard 智能问答</h2>
              <p className="text-sm text-slate-400 max-w-sm">
                基于知识库的智能问答，自动检测并提示信息冲突。
                <br />点击左侧「+」开始新对话。
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-6">
              {messages.length === 0 && !loading && (
                <div className="text-center py-20">
                  <p className="text-sm text-slate-400">发送第一条消息开始对话</p>
                </div>
              )}
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {loading && (
                <div className="flex justify-start mb-4">
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                    <Loader2 size={18} className="animate-spin text-indigo-400" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <ChatInput onSend={sendMessage} disabled={loading} />
          </>
        )}
      </div>
    </div>
  )
}

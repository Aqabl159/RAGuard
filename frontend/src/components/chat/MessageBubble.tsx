import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { QAMessage } from '../../types'
import SourceCard from './SourceCard'
import ConflictWarning from './ConflictWarning'

interface Props {
  message: QAMessage
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? 'order-1' : ''}`}>
        {/* Avatar row */}
        <div className={`flex items-center gap-2 mb-1 ${isUser ? 'justify-end' : ''}`}>
          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
            isUser ? 'bg-indigo-100 text-indigo-600 order-2' : 'bg-slate-200 text-slate-600'
          }`}>
            {isUser ? 'U' : 'AI'}
          </div>
          <span className="text-xs text-slate-400">
            {isUser ? '你' : 'RAGuard'}
          </span>
        </div>

        {/* Content */}
        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-md'
            : 'bg-white border border-slate-200 text-slate-700 rounded-bl-md shadow-sm'
        }`}>
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-slate">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Sources (assistant only) */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <SourceCard sources={message.sources} />
          )}

          {/* Conflict warning (assistant only) */}
          {!isUser && message.conflict_warning && (
            <ConflictWarning warning={message.conflict_warning} />
          )}
        </div>

        {/* Meta */}
        {message.latency_ms && (
          <p className={`text-xs text-slate-400 mt-1 ${isUser ? 'text-right' : ''}`}>
            {(message.latency_ms / 1000).toFixed(1)}s
          </p>
        )}
      </div>
    </div>
  )
}

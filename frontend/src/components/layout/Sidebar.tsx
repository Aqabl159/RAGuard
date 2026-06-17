import { NavLink } from 'react-router-dom'
import {
  MessageSquare,
  Shield,
  FolderOpen,
  History,
  Scan,
} from 'lucide-react'

const navItems = [
  { to: '/chat', icon: MessageSquare, label: '智能问答' },
  { to: '/governance', icon: Shield, label: '冲突治理' },
  { to: '/documents', icon: FolderOpen, label: '文档管理' },
  { to: '/audit', icon: History, label: '审计日志' },
]

export default function Sidebar() {
  return (
    <aside className="w-60 bg-slate-900 text-slate-300 flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-700">
        <h1 className="text-xl font-bold text-white tracking-tight">
          <span className="text-indigo-400">RAG</span>uard
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">知识库冲突检测引擎</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Scan trigger */}
      <div className="px-4 py-4 border-t border-slate-700">
        <button
          onClick={() => {
            fetch('/api/scans/start', { method: 'POST' })
              .then(() => alert('扫描任务已启动'))
              .catch(() => alert('启动扫描失败'))
          }}
          className="flex items-center justify-center gap-2 w-full px-3 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Scan size={16} />
          启动离线扫描
        </button>
      </div>
    </aside>
  )
}

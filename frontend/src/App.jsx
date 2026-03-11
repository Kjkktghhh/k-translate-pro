import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Layers, BookOpen, BarChart2, Zap } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import NewBatch from './pages/NewBatch'
import BatchDetail from './pages/BatchDetail'
import Glossaries from './pages/Glossaries'
import clsx from 'clsx'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/batches/new', icon: Layers, label: 'New Batch' },
  { to: '/glossaries', icon: BookOpen, label: 'Glossaries' },
]

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 flex flex-col border-r border-ink-700/50 bg-ink-900/80">
        {/* Logo */}
        <div className="px-5 py-6 border-b border-ink-700/50">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-coral-500 flex items-center justify-center">
              <Zap size={14} className="text-white" />
            </div>
            <div>
              <div className="font-display text-sm text-white leading-none">K-Translate</div>
              <div className="font-mono text-[10px] text-ink-400 leading-none mt-0.5">Pro</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all',
                isActive
                  ? 'bg-coral-500/15 text-coral-400 border border-coral-500/20'
                  : 'text-ink-300 hover:text-white hover:bg-ink-700/50'
              )}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-ink-700/50">
          <div className="text-[11px] text-ink-500 font-mono">v1.0.0-mvp</div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-ink-900">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/batches/new" element={<NewBatch />} />
          <Route path="/batches/:id" element={<BatchDetail />} />
          <Route path="/glossaries" element={<Glossaries />} />
        </Routes>
      </main>
    </div>
  )
}

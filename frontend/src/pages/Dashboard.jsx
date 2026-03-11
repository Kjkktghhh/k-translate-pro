import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { batchesAPI } from '../lib/api'
import { Clock, CheckCircle, AlertCircle, Loader2, Plus, ChevronRight, Image } from 'lucide-react'
import clsx from 'clsx'

const STATUS_CONFIG = {
  queued:         { label: 'Queued',        color: 'text-ink-400',   dot: 'bg-ink-500' },
  preprocessing:  { label: 'Preprocessing', color: 'text-blue-400',  dot: 'bg-blue-400 animate-pulse' },
  ocr:            { label: 'OCR',           color: 'text-blue-400',  dot: 'bg-blue-400 animate-pulse' },
  translating:    { label: 'Translating',   color: 'text-yellow-400',dot: 'bg-yellow-400 animate-pulse' },
  reconstructing: { label: 'Rendering',     color: 'text-purple-400',dot: 'bg-purple-400 animate-pulse' },
  review_ready:   { label: 'Review Ready',  color: 'text-coral-400', dot: 'bg-coral-400' },
  complete:       { label: 'Complete',      color: 'text-green-400', dot: 'bg-green-400' },
  failed:         { label: 'Failed',        color: 'text-red-400',   dot: 'bg-red-400' },
}

function ProgressBar({ processed, total }) {
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0
  return (
    <div className="w-full h-1 bg-ink-700 rounded-full overflow-hidden">
      <div
        className="h-full bg-coral-500 rounded-full transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export default function Dashboard() {
  const [batches, setBatches] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = () => batchesAPI.list().then(r => setBatches(r.data)).catch(console.error)
    load()
    setLoading(false)
    // Poll for active batches
    const timer = setInterval(load, 4000)
    return () => clearInterval(timer)
  }, [])

  const active = batches.filter(b => !['complete', 'failed', 'review_ready'].includes(b.status))
  const ready = batches.filter(b => b.status === 'review_ready')
  const done = batches.filter(b => b.status === 'complete')

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-3xl text-white">Dashboard</h1>
          <p className="text-ink-400 text-sm mt-1">Korean image localization pipeline</p>
        </div>
        <Link
          to="/batches/new"
          className="flex items-center gap-2 px-4 py-2 bg-coral-500 hover:bg-coral-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={15} />
          New Batch
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Processing', value: active.length, icon: Loader2, color: 'text-blue-400', iconClass: active.length > 0 ? 'animate-spin' : '' },
          { label: 'Awaiting Review', value: ready.length, icon: AlertCircle, color: 'text-coral-400', iconClass: '' },
          { label: 'Completed', value: done.length, icon: CheckCircle, color: 'text-green-400', iconClass: '' },
        ].map(({ label, value, icon: Icon, color, iconClass }) => (
          <div key={label} className="glass rounded-xl p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-ink-400 text-sm">{label}</span>
              <Icon size={18} className={clsx(color, iconClass)} />
            </div>
            <div className="text-3xl font-display text-white">{value}</div>
          </div>
        ))}
      </div>

      {/* Batch list */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-ink-700/50 flex items-center justify-between">
          <h2 className="text-sm font-medium text-white">Recent Batches</h2>
          <span className="text-ink-500 text-xs font-mono">{batches.length} total</span>
        </div>

        {loading ? (
          <div className="p-10 text-center text-ink-500">
            <Loader2 size={20} className="animate-spin mx-auto mb-2" />
          </div>
        ) : batches.length === 0 ? (
          <div className="p-12 text-center">
            <Image size={32} className="text-ink-600 mx-auto mb-3" />
            <p className="text-ink-400 text-sm">No batches yet.</p>
            <Link to="/batches/new" className="text-coral-400 text-sm hover:underline mt-1 inline-block">
              Create your first batch →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-ink-700/30">
            {batches.map(batch => {
              const cfg = STATUS_CONFIG[batch.status] || STATUS_CONFIG.queued
              const pct = batch.total_images > 0
                ? Math.round((batch.processed_images / batch.total_images) * 100)
                : 0

              return (
                <Link
                  key={batch.id}
                  to={`/batches/${batch.id}`}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-ink-700/20 transition-colors group"
                >
                  <div className={clsx('w-2 h-2 rounded-full flex-shrink-0', cfg.dot)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-medium text-white truncate">{batch.name}</span>
                      <span className={clsx('text-xs ml-3 flex-shrink-0', cfg.color)}>{cfg.label}</span>
                    </div>
                    <ProgressBar processed={batch.processed_images} total={batch.total_images} />
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="text-xs text-ink-500 font-mono">
                        {batch.processed_images}/{batch.total_images} images
                      </span>
                      {batch.avg_confidence && (
                        <span className="text-xs text-ink-500 font-mono">
                          {batch.avg_confidence.toFixed(1)}% conf
                        </span>
                      )}
                      <span className="text-xs text-ink-600 font-mono ml-auto">
                        {new Date(batch.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <ChevronRight size={14} className="text-ink-600 group-hover:text-ink-400 transition-colors flex-shrink-0" />
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

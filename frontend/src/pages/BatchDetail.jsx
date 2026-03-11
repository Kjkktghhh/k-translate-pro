import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { batchesAPI, imagesAPI } from '../lib/api'
import { ArrowLeft, Download, CheckCheck, Loader2, Eye, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import clsx from 'clsx'

const FILTERS = [
  { value: null,     label: 'All' },
  { value: 'high',   label: '✓ High' },
  { value: 'medium', label: '◑ Medium' },
  { value: 'low',    label: '⚠ Low' },
  { value: 'flagged',label: '⚑ Flagged' },
]

const STATUS_ICONS = {
  high_confidence:   <CheckCircle size={12} className="text-green-400" />,
  medium_confidence: <CheckCircle size={12} className="text-yellow-400" />,
  low_confidence:    <AlertTriangle size={12} className="text-coral-400" />,
  flagged:           <AlertTriangle size={12} className="text-red-400" />,
  approved:          <CheckCheck size={12} className="text-green-500" />,
  processing:        <Loader2 size={12} className="text-blue-400 animate-spin" />,
  pending:           <Loader2 size={12} className="text-ink-500 animate-spin" />,
  failed:            <XCircle size={12} className="text-red-400" />,
}

const CONF_COLOR = (score) => {
  if (!score) return 'text-ink-500'
  if (score >= 90) return 'text-green-400'
  if (score >= 70) return 'text-yellow-400'
  return 'text-coral-400'
}

function ImageCard({ job, onApprove, selectedLang }) {
  const [preview, setPreview] = useState(false)
  const outputUrl = imagesAPI.outputUrl(job.id, selectedLang)
  const origUrl = imagesAPI.originalUrl(job.id)

  return (
    <div className="glass rounded-xl overflow-hidden group">
      {/* Thumbnail */}
      <div className="relative aspect-square bg-ink-800 overflow-hidden">
        {job.output_path_zh_hant || job.output_path_en ? (
          <img
            src={outputUrl}
            alt={job.filename}
            className="w-full h-full object-cover"
            onError={e => { e.target.src = origUrl }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Loader2 size={20} className="text-ink-600 animate-spin" />
          </div>
        )}
        
        {/* Overlay actions */}
        <div className="absolute inset-0 bg-ink-900/70 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <button
            onClick={() => setPreview(true)}
            className="p-2 bg-ink-800 rounded-lg hover:bg-ink-700 text-white transition-colors"
          >
            <Eye size={14} />
          </button>
          {job.status !== 'approved' && (
            <button
              onClick={() => onApprove(job.id)}
              className="p-2 bg-green-500/20 rounded-lg hover:bg-green-500/40 text-green-400 transition-colors"
            >
              <CheckCheck size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="px-3 py-2.5">
        <div className="flex items-center gap-1.5 mb-1">
          {STATUS_ICONS[job.status] || null}
          <span className="text-[11px] text-ink-400 truncate flex-1">{job.filename}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className={clsx('text-xs font-mono', CONF_COLOR(job.confidence_score))}>
            {job.confidence_score ? `${job.confidence_score}%` : '—'}
          </span>
          <span className="text-[10px] text-ink-600 font-mono">
            {job.ocr_data ? `${job.ocr_data.total_blocks || 0} blocks` : ''}
          </span>
        </div>
      </div>

      {/* Preview modal */}
      {preview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/90" onClick={() => setPreview(false)}>
          <div className="max-w-4xl w-full mx-4 glass rounded-xl overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-ink-700">
              <span className="text-sm font-medium text-white">{job.filename}</span>
              <button onClick={() => setPreview(false)} className="text-ink-400 hover:text-white">✕</button>
            </div>
            <div className="grid grid-cols-2 gap-0">
              <div className="p-3">
                <div className="text-xs text-ink-500 mb-2 font-mono">ORIGINAL</div>
                <img src={origUrl} alt="original" className="w-full rounded-lg" />
              </div>
              <div className="p-3 border-l border-ink-700">
                <div className="text-xs text-ink-500 mb-2 font-mono">TRANSLATED ({selectedLang})</div>
                <img src={outputUrl} alt="translated" className="w-full rounded-lg" onError={e => e.target.src = origUrl} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function BatchDetail() {
  const { id } = useParams()
  const [batch, setBatch] = useState(null)
  const [images, setImages] = useState([])
  const [filter, setFilter] = useState(null)
  const [selectedLang, setSelectedLang] = useState('zh-Hant')
  const [loading, setLoading] = useState(true)

  const isActive = batch && !['complete', 'review_ready', 'failed'].includes(batch?.status)

  useEffect(() => {
    const load = async () => {
      try {
        const [bRes, iRes] = await Promise.all([
          batchesAPI.get(id),
          batchesAPI.getImages(id, filter)
        ])
        setBatch(bRes.data)
        setImages(iRes.data)
      } catch (e) {
        console.error(e)
      }
      setLoading(false)
    }
    load()
    if (isActive) {
      const t = setInterval(load, 3000)
      return () => clearInterval(t)
    }
  }, [id, filter, isActive])

  const handleApprove = async (imageId) => {
    await batchesAPI.approve(id, imageId)
    setImages(prev => prev.map(img =>
      img.id === imageId ? { ...img, status: 'approved' } : img
    ))
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <Loader2 size={24} className="animate-spin text-ink-500" />
    </div>
  )

  if (!batch) return (
    <div className="p-8 text-center text-ink-400">Batch not found</div>
  )

  const pct = batch.total_images > 0
    ? Math.round((batch.processed_images / batch.total_images) * 100) : 0

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link to="/" className="flex items-center gap-1.5 text-ink-500 hover:text-white text-sm mb-3 transition-colors">
            <ArrowLeft size={14} /> Dashboard
          </Link>
          <h1 className="font-display text-2xl text-white">{batch.name}</h1>
          <p className="text-ink-400 text-sm mt-1 font-mono">
            {batch.processed_images}/{batch.total_images} processed ·{' '}
            {batch.avg_confidence ? `${batch.avg_confidence.toFixed(1)}% avg confidence` : 'processing…'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Language toggle */}
          <div className="flex glass rounded-lg overflow-hidden">
            {['zh-Hant', 'en'].map(lang => (
              <button
                key={lang}
                onClick={() => setSelectedLang(lang)}
                className={clsx(
                  'px-3 py-1.5 text-xs font-mono transition-colors',
                  selectedLang === lang ? 'bg-coral-500 text-white' : 'text-ink-400 hover:text-white'
                )}
              >
                {lang}
              </button>
            ))}
          </div>
          <a
            href={batchesAPI.exportZip(id)}
            className="flex items-center gap-2 px-4 py-2 glass hover:bg-ink-700/50 text-white rounded-lg text-sm transition-colors"
          >
            <Download size={14} />
            Export ZIP
          </a>
        </div>
      </div>

      {/* Progress bar */}
      {isActive && (
        <div className="glass rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-ink-300 capitalize">{batch.status.replace('_', ' ')}…</span>
            <span className="text-sm font-mono text-coral-400">{pct}%</span>
          </div>
          <div className="h-1.5 bg-ink-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-coral-500 rounded-full transition-all duration-700"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2 mb-5">
        {FILTERS.map(f => (
          <button
            key={String(f.value)}
            onClick={() => setFilter(f.value)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
              filter === f.value
                ? 'bg-coral-500/20 text-coral-400 border border-coral-500/30'
                : 'glass text-ink-400 hover:text-white'
            )}
          >
            {f.label}
            {f.value === null && ` (${images.length})`}
          </button>
        ))}
      </div>

      {/* Image grid */}
      {images.length === 0 ? (
        <div className="text-center py-12 text-ink-500">
          {isActive ? 'Images are being processed…' : 'No images match this filter'}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
          {images.map(job => (
            <ImageCard
              key={job.id}
              job={job}
              onApprove={handleApprove}
              selectedLang={selectedLang}
            />
          ))}
        </div>
      )}
    </div>
  )
}

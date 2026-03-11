import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { batchesAPI, glossariesAPI } from '../lib/api'
import { Upload, X, FileImage, Loader2, ChevronDown } from 'lucide-react'
import clsx from 'clsx'

const LANGUAGES = [
  { code: 'zh-Hant', label: '繁體中文', sublabel: 'Traditional Chinese' },
  { code: 'en',      label: 'English',  sublabel: 'English' },
]

function FileThumb({ file, onRemove }) {
  const url = URL.createObjectURL(file)
  return (
    <div className="relative group aspect-square rounded-lg overflow-hidden bg-ink-800 border border-ink-700">
      <img src={url} alt={file.name} className="w-full h-full object-cover" />
      <div className="absolute inset-0 bg-ink-900/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
        <button onClick={() => onRemove(file)} className="text-white hover:text-red-400 transition-colors">
          <X size={18} />
        </button>
      </div>
      <div className="absolute bottom-0 inset-x-0 px-1.5 py-1 bg-ink-900/80 text-[9px] text-ink-400 truncate">
        {file.name}
      </div>
    </div>
  )
}

export default function NewBatch() {
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [batchName, setBatchName] = useState('')
  const [selectedLangs, setSelectedLangs] = useState(['zh-Hant', 'en'])
  const [glossaryId, setGlossaryId] = useState('')
  const [glossaries, setGlossaries] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    glossariesAPI.list().then(r => setGlossaries(r.data)).catch(() => {})
  }, [])

  const onDrop = useCallback(accepted => {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name + f.size))
      const newFiles = accepted.filter(f => !existing.has(f.name + f.size))
      return [...prev, ...newFiles].slice(0, 500)
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'] },
    maxSize: 25 * 1024 * 1024,
  })

  const toggleLang = (code) => {
    setSelectedLangs(prev =>
      prev.includes(code) ? prev.filter(l => l !== code) : [...prev, code]
    )
  }

  const handleSubmit = async () => {
    if (!files.length) { setError('Add at least one image'); return }
    if (!batchName.trim()) { setError('Enter a batch name'); return }
    if (!selectedLangs.length) { setError('Select at least one language'); return }
    
    setLoading(true)
    setError('')
    
    const fd = new FormData()
    fd.append('name', batchName)
    fd.append('target_languages', JSON.stringify(selectedLangs))
    if (glossaryId) fd.append('glossary_id', glossaryId)
    files.forEach(f => fd.append('files', f))
    
    try {
      const res = await batchesAPI.create(fd)
      navigate(`/batches/${res.data.id}`)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create batch')
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl text-white">New Batch</h1>
        <p className="text-ink-400 text-sm mt-1">Upload Korean product images for localization</p>
      </div>

      <div className="grid grid-cols-5 gap-6">
        {/* Left: Settings */}
        <div className="col-span-2 space-y-5">
          {/* Batch name */}
          <div className="glass rounded-xl p-5">
            <label className="text-xs font-medium text-ink-400 uppercase tracking-wider block mb-3">
              Batch Name
            </label>
            <input
              type="text"
              value={batchName}
              onChange={e => setBatchName(e.target.value)}
              placeholder="e.g. Brand X Summer 2026"
              className="w-full bg-ink-800 border border-ink-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-ink-500 focus:outline-none focus:border-coral-500 transition-colors"
            />
          </div>

          {/* Target languages */}
          <div className="glass rounded-xl p-5">
            <label className="text-xs font-medium text-ink-400 uppercase tracking-wider block mb-3">
              Target Languages
            </label>
            <div className="space-y-2">
              {LANGUAGES.map(lang => (
                <button
                  key={lang.code}
                  onClick={() => toggleLang(lang.code)}
                  className={clsx(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-all',
                    selectedLangs.includes(lang.code)
                      ? 'bg-coral-500/15 border-coral-500/40 text-white'
                      : 'border-ink-700 text-ink-400 hover:border-ink-500'
                  )}
                >
                  <div className={clsx(
                    'w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center',
                    selectedLangs.includes(lang.code) ? 'bg-coral-500 border-coral-500' : 'border-ink-600'
                  )}>
                    {selectedLangs.includes(lang.code) && (
                      <svg width="8" height="8" viewBox="0 0 8 8"><path d="M1 4l2 2 4-4" stroke="white" strokeWidth="1.5" fill="none"/></svg>
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-medium">{lang.label}</div>
                    <div className="text-xs text-ink-500">{lang.sublabel}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Glossary */}
          <div className="glass rounded-xl p-5">
            <label className="text-xs font-medium text-ink-400 uppercase tracking-wider block mb-3">
              Brand Glossary
            </label>
            <div className="relative">
              <select
                value={glossaryId}
                onChange={e => setGlossaryId(e.target.value)}
                className="w-full bg-ink-800 border border-ink-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-coral-500 appearance-none"
              >
                <option value="">No glossary</option>
                {glossaries.map(g => (
                  <option key={g.id} value={g.id}>{g.name} ({g.entry_count} terms)</option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-500 pointer-events-none" />
            </div>
          </div>

          {/* Submit */}
          {error && (
            <div className="text-red-400 text-sm bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          <button
            onClick={handleSubmit}
            disabled={loading || !files.length}
            className="w-full flex items-center justify-center gap-2 py-3 bg-coral-500 hover:bg-coral-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl font-medium text-sm transition-colors"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            {loading ? 'Uploading…' : `Process ${files.length} Image${files.length !== 1 ? 's' : ''}`}
          </button>
        </div>

        {/* Right: Drop zone + previews */}
        <div className="col-span-3">
          <div
            {...getRootProps()}
            className={clsx(
              'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all mb-4',
              isDragActive
                ? 'border-coral-400 bg-coral-500/10'
                : 'border-ink-700 hover:border-ink-500 hover:bg-ink-800/30'
            )}
          >
            <input {...getInputProps()} />
            <Upload size={28} className={clsx('mx-auto mb-3', isDragActive ? 'text-coral-400' : 'text-ink-500')} />
            <p className="text-sm text-white font-medium">Drop images here</p>
            <p className="text-xs text-ink-500 mt-1">JPG, PNG, TIFF, WebP · max 25 MB each · up to 500 images</p>
          </div>

          {files.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-ink-400 font-mono">{files.length} files selected</span>
                <button onClick={() => setFiles([])} className="text-xs text-red-400 hover:underline">
                  Clear all
                </button>
              </div>
              <div className="grid grid-cols-5 gap-2 max-h-72 overflow-y-auto pr-1">
                {files.map(f => (
                  <FileThumb key={f.name + f.size} file={f} onRemove={f => setFiles(p => p.filter(x => x !== f))} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

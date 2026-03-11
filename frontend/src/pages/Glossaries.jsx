import { useState, useEffect, useRef } from 'react'
import { glossariesAPI } from '../lib/api'
import { Plus, Trash2, Upload, BookOpen, ChevronDown, ChevronRight } from 'lucide-react'

function GlossaryCard({ glossary, onDelete }) {
  const [entries, setEntries] = useState([])
  const [expanded, setExpanded] = useState(false)
  const [adding, setAdding] = useState(false)
  const [newEntry, setNewEntry] = useState({ korean: '', zh_hant: '', english: '', category: '', do_not_translate: false })
  const fileRef = useRef()

  const loadEntries = async () => {
    const res = await glossariesAPI.getEntries(glossary.id)
    setEntries(res.data)
  }

  const handleExpand = () => {
    if (!expanded) loadEntries()
    setExpanded(e => !e)
  }

  const handleAddEntry = async () => {
    if (!newEntry.korean) return
    await glossariesAPI.addEntry(glossary.id, newEntry)
    setNewEntry({ korean: '', zh_hant: '', english: '', category: '', do_not_translate: false })
    setAdding(false)
    loadEntries()
  }

  const handleCsvUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    await glossariesAPI.uploadCsv(glossary.id, file)
    loadEntries()
    e.target.value = ''
  }

  return (
    <div className="glass rounded-xl overflow-hidden">
      <div
        className="flex items-center gap-3 px-5 py-4 cursor-pointer hover:bg-ink-700/20 transition-colors"
        onClick={handleExpand}
      >
        {expanded ? <ChevronDown size={14} className="text-ink-400" /> : <ChevronRight size={14} className="text-ink-400" />}
        <BookOpen size={16} className="text-coral-400" />
        <div className="flex-1">
          <div className="text-sm font-medium text-white">{glossary.name}</div>
          {glossary.description && <div className="text-xs text-ink-500 mt-0.5">{glossary.description}</div>}
        </div>
        <div className="text-xs font-mono text-ink-400">{glossary.entry_count} terms</div>
        <button
          onClick={e => { e.stopPropagation(); onDelete(glossary.id) }}
          className="text-ink-600 hover:text-red-400 transition-colors ml-2"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {expanded && (
        <div className="border-t border-ink-700/50">
          {/* Actions */}
          <div className="flex items-center gap-2 px-5 py-3 bg-ink-800/30">
            <button
              onClick={() => setAdding(a => !a)}
              className="flex items-center gap-1.5 text-xs text-coral-400 hover:text-coral-300 transition-colors"
            >
              <Plus size={12} /> Add term
            </button>
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-1.5 text-xs text-ink-400 hover:text-white transition-colors ml-3"
            >
              <Upload size={12} /> Import CSV
            </button>
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleCsvUpload} />
            <span className="text-xs text-ink-600 ml-auto font-mono">
              Columns: Korean | zh-Hant | English | Category | DoNotTranslate
            </span>
          </div>

          {/* Add form */}
          {adding && (
            <div className="px-5 py-3 bg-ink-800/50 border-b border-ink-700/30 grid grid-cols-5 gap-2">
              {['korean', 'zh_hant', 'english', 'category'].map(field => (
                <input
                  key={field}
                  placeholder={field.replace('_', '-')}
                  value={newEntry[field]}
                  onChange={e => setNewEntry(p => ({ ...p, [field]: e.target.value }))}
                  className="bg-ink-900 border border-ink-700 rounded px-2 py-1.5 text-xs text-white placeholder-ink-600 focus:outline-none focus:border-coral-500"
                />
              ))}
              <button
                onClick={handleAddEntry}
                className="px-3 py-1.5 bg-coral-500 hover:bg-coral-600 text-white text-xs rounded transition-colors"
              >
                Add
              </button>
            </div>
          )}

          {/* Entries table */}
          {entries.length > 0 ? (
            <div className="overflow-x-auto max-h-64 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-ink-800">
                  <tr className="text-ink-500">
                    <th className="text-left px-5 py-2 font-medium">Korean</th>
                    <th className="text-left px-3 py-2 font-medium">繁中</th>
                    <th className="text-left px-3 py-2 font-medium">English</th>
                    <th className="text-left px-3 py-2 font-medium">Category</th>
                    <th className="text-left px-3 py-2 font-medium">DNT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-700/30">
                  {entries.map((e, i) => (
                    <tr key={i} className="hover:bg-ink-700/20">
                      <td className="px-5 py-2 text-white font-medium">{e.korean}</td>
                      <td className="px-3 py-2 text-ink-300">{e.zh_hant}</td>
                      <td className="px-3 py-2 text-ink-300">{e.english}</td>
                      <td className="px-3 py-2 text-ink-500">{e.category || '—'}</td>
                      <td className="px-3 py-2">
                        {e.do_not_translate ? <span className="text-coral-400">Y</span> : <span className="text-ink-600">N</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-5 py-6 text-center text-ink-500 text-xs">
              No entries yet. Add terms manually or import a CSV.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Glossaries() {
  const [glossaries, setGlossaries] = useState([])
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const load = () => glossariesAPI.list().then(r => setGlossaries(r.data))
  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    await glossariesAPI.create({ name: newName, description: newDesc })
    setNewName(''); setNewDesc(''); setCreating(false)
    load()
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this glossary?')) return
    await glossariesAPI.delete(id)
    load()
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-3xl text-white">Glossaries</h1>
          <p className="text-ink-400 text-sm mt-1">Enforce brand terminology across all translations</p>
        </div>
        <button
          onClick={() => setCreating(c => !c)}
          className="flex items-center gap-2 px-4 py-2 bg-coral-500 hover:bg-coral-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={15} /> New Glossary
        </button>
      </div>

      {creating && (
        <div className="glass rounded-xl p-5 mb-5">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <input
              placeholder="Glossary name"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              className="bg-ink-800 border border-ink-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-ink-500 focus:outline-none focus:border-coral-500 col-span-1"
            />
            <input
              placeholder="Description (optional)"
              value={newDesc}
              onChange={e => setNewDesc(e.target.value)}
              className="bg-ink-800 border border-ink-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-ink-500 focus:outline-none focus:border-coral-500 col-span-1"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-2 bg-coral-500 hover:bg-coral-600 text-white rounded-lg text-sm transition-colors">
              Create
            </button>
            <button onClick={() => setCreating(false)} className="px-4 py-2 glass text-ink-400 hover:text-white rounded-lg text-sm transition-colors">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {glossaries.length === 0 ? (
          <div className="glass rounded-xl p-12 text-center">
            <BookOpen size={32} className="text-ink-600 mx-auto mb-3" />
            <p className="text-ink-400 text-sm">No glossaries yet.</p>
            <p className="text-ink-600 text-xs mt-1">Create one to enforce brand terminology in translations.</p>
          </div>
        ) : (
          glossaries.map(g => (
            <GlossaryCard key={g.id} glossary={g} onDelete={handleDelete} />
          ))
        )}
      </div>
    </div>
  )
}

import { useEffect, useMemo, useRef, useState } from 'react'
import { useLang } from '@/docs'

interface Hit {
  sectionId: string
  sectionTitle: string
  headingId?: string
  heading?: string
  snippet: string
}

interface Props {
  open: boolean
  onClose: () => void
  onNavigate: (sectionId: string, headingId?: string) => void
}

function stripMd(s: string): string {
  return s.replace(/`([^`]+)`/g, '$1').replace(/\*\*([^*]+)\*\*/g, '$1')
}

export function SearchModal({ open, onClose, onNavigate }: Props) {
  const { t } = useLang()
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [open])

  const hits = useMemo<Hit[]>(() => {
    const q = query.trim().toLowerCase()
    if (!q) return []
    const out: Hit[] = []
    for (const s of t.sections) {
      if (s.title.toLowerCase().includes(q)) {
        out.push({ sectionId: s.id, sectionTitle: s.title, snippet: stripMd(s.lead ?? '').slice(0, 140) })
      }
      let h3 = 0
      for (const b of s.blocks) {
        if (b.type === 'h3') {
          const id = `h-${h3++}`
          if (b.text.toLowerCase().includes(q)) {
            out.push({ sectionId: s.id, sectionTitle: s.title, headingId: id, heading: b.text, snippet: '' })
          }
          continue
        }
        const text =
          b.type === 'p' || b.type === 'callout'
            ? b.text
            : b.type === 'list'
              ? b.items.join(' ')
              : b.type === 'table'
                ? b.rows.flat().join(' ')
                : b.type === 'code'
                  ? b.code
                  : b.type === 'steps'
                    ? b.items.map((x) => x.title + ' ' + x.text).join(' ')
                    : ''
        const idx = text.toLowerCase().indexOf(q)
        if (idx >= 0) {
          const clean = stripMd(text)
          const start = Math.max(0, idx - 50)
          out.push({
            sectionId: s.id,
            sectionTitle: s.title,
            snippet: (start > 0 ? '…' : '') + clean.slice(start, start + 130) + '…',
          })
        }
        if (out.length >= 24) break
      }
      if (out.length >= 24) break
    }
    return out.slice(0, 24)
  }, [query, t])

  useEffect(() => setSelected(0), [hits.length])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelected((s) => Math.min(s + 1, hits.length - 1))
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelected((s) => Math.max(s - 1, 0))
      }
      if (e.key === 'Enter' && hits[selected]) {
        onNavigate(hits[selected].sectionId, hits[selected].headingId)
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, hits, selected, onClose, onNavigate])

  if (!open) return null

  return (
    <div className="search-overlay" onClick={onClose}>
      <div className="search-panel" onClick={(e) => e.stopPropagation()}>
        <div className="search-input-row">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4 shrink-0 opacity-60">
            <circle cx="7" cy="7" r="5" />
            <path d="M11 11l3 3" strokeLinecap="round" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.nav.searchPlaceholder}
            className="search-input"
          />
          <kbd className="topbar-kbd">ESC</kbd>
        </div>
        <div className="search-results">
          {query && hits.length === 0 && <div className="search-empty">{t.nav.searchEmpty}</div>}
          {hits.map((h, i) => (
            <button
              key={`${h.sectionId}-${h.headingId ?? ''}-${i}`}
              type="button"
              className={`search-hit ${i === selected ? 'search-hit-active' : ''}`}
              onMouseEnter={() => setSelected(i)}
              onClick={() => {
                onNavigate(h.sectionId, h.headingId)
                onClose()
              }}
            >
              <div className="search-hit-title">
                {h.heading ? `${h.sectionTitle} · ${h.heading}` : h.sectionTitle}
              </div>
              {h.snippet && <div className="search-hit-snippet">{h.snippet}</div>}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

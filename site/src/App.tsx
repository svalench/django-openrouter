import { useCallback, useEffect, useMemo, useState } from 'react'
import { LangContext, detectLang, getContent, useLang, type Lang } from '@/docs'
import { Blocks, sectionHeadings } from '@/components/Blocks'
import { Sidebar } from '@/components/Sidebar'
import { TopBar } from '@/components/TopBar'
import { SearchModal } from '@/components/SearchModal'
import { Toc } from '@/components/Toc'
import { RichText } from '@/components/RichText'

type Theme = 'light' | 'dark'

function detectTheme(): Theme {
  try {
    const saved = localStorage.getItem('dor-theme')
    if (saved === 'light' || saved === 'dark') return saved
  } catch {
    /* noop */
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function currentSectionFromHash(sections: { id: string }[]): string {
  const h = window.location.hash
  const m = h.match(/^#\/([\w-]+)/)
  if (m && sections.some((s) => s.id === m[1])) return m[1]
  return sections[0]?.id ?? ''
}

export default function App() {
  const [lang, setLangState] = useState<Lang>(detectLang)
  const [theme, setTheme] = useState<Theme>(detectTheme)
  const t = getContent(lang)
  const [section, setSection] = useState(() => currentSectionFromHash(t.sections))
  const [searchOpen, setSearchOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    try {
      localStorage.setItem('dor-lang', l)
    } catch {
      /* noop */
    }
  }, [])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try {
      localStorage.setItem('dor-theme', theme)
    } catch {
      /* noop */
    }
  }, [theme])

  useEffect(() => {
    document.documentElement.lang = lang
    document.title = `${t.meta.name} — ${t.sections.find((s) => s.id === section)?.title ?? 'docs'}`
  }, [lang, section, t])

  const navigate = useCallback((id: string, headingId?: string) => {
    window.location.hash = `#/${id}`
    setSection(id)
    setMenuOpen(false)
    requestAnimationFrame(() => {
      if (headingId) {
        document.getElementById(headingId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      } else {
        window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
      }
    })
  }, [])

  useEffect(() => {
    const onHash = () => setSection(currentSectionFromHash(t.sections))
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [t])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const active = t.sections.find((s) => s.id === section) ?? t.sections[0]
  const headings = useMemo(() => sectionHeadings(active.blocks), [active])
  const idx = t.sections.findIndex((s) => s.id === active.id)
  const prev = idx > 0 ? t.sections[idx - 1] : null
  const next = idx < t.sections.length - 1 ? t.sections[idx + 1] : null

  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      <div className="app-shell">
        <TopBar
          theme={theme}
          onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          onOpenSearch={() => setSearchOpen(true)}
          onOpenMenu={() => setMenuOpen(true)}
        />

        {/* mobile drawer */}
        {menuOpen && (
          <div className="drawer-overlay" onClick={() => setMenuOpen(false)}>
            <div className="drawer" onClick={(e) => e.stopPropagation()}>
              <div className="drawer-head">
                <Brand />
                <button type="button" className="topbar-icon-btn" onClick={() => setMenuOpen(false)} aria-label={t.ui.closeMenu}>
                  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4">
                    <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
              <Sidebar active={active.id} onNavigate={(id) => navigate(id)} />
            </div>
          </div>
        )}

        <div className="app-body">
          <aside className="app-sidebar">
            <div className="sidebar-brand-row">
              <Brand />
            </div>
            <Sidebar active={active.id} onNavigate={(id) => navigate(id)} />
            <div className="sidebar-footer">
              <a href={t.meta.github} target="_blank" rel="noreferrer" className="sidebar-foot-link">
                GitHub ↗
              </a>
              <a href={t.meta.pypi} target="_blank" rel="noreferrer" className="sidebar-foot-link">
                PyPI ↗
              </a>
              <span className="sidebar-foot-meta">v{t.meta.version} · {t.nav.license}</span>
            </div>
          </aside>

          <main className="app-main">
            <article className="doc-article" key={`${lang}-${active.id}`}>
              <div className="doc-crumb">{active.group}</div>
              <h1 className="doc-h1">{active.title}</h1>
              {active.lead && (
                <p className="doc-lead">
                  <RichText text={active.lead} />
                </p>
              )}
              {active.id === 'intro' && <Hero onStart={() => navigate('quickstart')} />}
              <Blocks blocks={active.blocks} />

              <div className="doc-pager">
                {prev ? (
                  <button type="button" className="doc-pager-btn" onClick={() => navigate(prev.id)}>
                    <span className="doc-pager-dir">← {t.nav.prev}</span>
                    <span className="doc-pager-title">{prev.title}</span>
                  </button>
                ) : (
                  <span />
                )}
                {next && (
                  <button type="button" className="doc-pager-btn doc-pager-next" onClick={() => navigate(next.id)}>
                    <span className="doc-pager-dir">{t.nav.next} →</span>
                    <span className="doc-pager-title">{next.title}</span>
                  </button>
                )}
              </div>
            </article>
          </main>

          <aside className="app-toc">
            <Toc headings={headings} />
          </aside>
        </div>

        <SearchModal open={searchOpen} onClose={() => setSearchOpen(false)} onNavigate={navigate} />
      </div>
    </LangContext.Provider>
  )
}

function Brand() {
  const { t } = useLang()
  return (
    <div className="brand">
      <span className="brand-mark" aria-hidden>
        <img src="logo.png" alt="" className="brand-logo" />
      </span>
      <span className="brand-name">{t.meta.name}</span>
      <span className="brand-version">v{t.meta.version}</span>
    </div>
  )
}

function Hero({ onStart }: { onStart: () => void }) {
  const { t } = useLang()
  return (
    <div className="hero">
      <div className="hero-badge">{t.nav.heroBadge}</div>
      <div className="hero-terminal">
        <div className="hero-terminal-bar">
          <span className="hero-dot" />
          <span className="hero-dot" />
          <span className="hero-dot" />
        </div>
        <code className="hero-terminal-line">
          <span className="tok-comment">$ </span>pip install django-openrouter
        </code>
      </div>
      <div className="hero-actions">
        <button type="button" className="hero-cta" onClick={onStart}>
          {t.nav.heroCta} →
        </button>
        <a href={t.meta.github} target="_blank" rel="noreferrer" className="hero-ghost">
          {t.nav.heroGithub} ↗
        </a>
      </div>
    </div>
  )
}

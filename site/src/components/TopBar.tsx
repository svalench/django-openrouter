import { LANGS, useLang, type Lang } from '@/docs'

interface Props {
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  onOpenSearch: () => void
  onOpenMenu: () => void
}

function GithubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className={className}>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}

export function TopBar({ theme, onToggleTheme, onOpenSearch, onOpenMenu }: Props) {
  const { lang, setLang, t } = useLang()

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button type="button" className="topbar-icon-btn lg:hidden" onClick={onOpenMenu} aria-label={t.ui.openMenu}>
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4.5 w-4.5">
            <path d="M2.5 4h11M2.5 8h11M2.5 12h11" strokeLinecap="round" />
          </svg>
        </button>

        <button type="button" className="topbar-search" onClick={onOpenSearch}>
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-3.5 w-3.5 shrink-0">
            <circle cx="7" cy="7" r="5" />
            <path d="M11 11l3 3" strokeLinecap="round" />
          </svg>
          <span className="topbar-search-label">{t.nav.searchPlaceholder}</span>
          <kbd className="topbar-kbd">⌘K</kbd>
        </button>

        <div className="flex items-center gap-1.5 ml-auto">
          <div className="lang-switch" role="group" aria-label={t.ui.language}>
            {LANGS.map((l) => (
              <button
                key={l.id}
                type="button"
                onClick={() => setLang(l.id as Lang)}
                title={l.label}
                className={`lang-btn ${lang === l.id ? 'lang-btn-active' : ''}`}
              >
                {l.short}
              </button>
            ))}
          </div>

          <button type="button" className="topbar-icon-btn" onClick={onToggleTheme} aria-label={t.ui.theme}>
            {theme === 'dark' ? (
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4">
                <circle cx="8" cy="8" r="3.2" />
                <path d="M8 1.5v1.6M8 12.9v1.6M1.5 8h1.6M12.9 8h1.6M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M12.6 3.4l-1.1 1.1M4.5 11.5l-1.1 1.1" strokeLinecap="round" />
              </svg>
            ) : (
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4">
                <path d="M13.5 9.5A5.8 5.8 0 0 1 6.5 2.5a5.8 5.8 0 1 0 7 7z" strokeLinejoin="round" />
              </svg>
            )}
          </button>

          <a
            href={t.meta.github}
            target="_blank"
            rel="noreferrer"
            className="topbar-icon-btn"
            aria-label={t.nav.editGithub}
          >
            <GithubIcon className="h-4 w-4" />
          </a>
        </div>
      </div>
    </header>
  )
}

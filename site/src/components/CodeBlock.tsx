import { useMemo, useState } from 'react'
import { highlight } from '@/lib/highlight'
import { useLang } from '@/docs'

interface Props {
  lang: string
  code: string
  title?: string
}

export function CodeBlock({ lang, code, title }: Props) {
  const { t } = useLang()
  const [copied, setCopied] = useState(false)
  const tokens = useMemo(() => highlight(code, lang), [code, lang])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = code
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      ta.remove()
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div className="codeblock group/code">
      <div className="codeblock-bar">
        <span className="codeblock-title">{title ?? lang}</span>
        <button
          type="button"
          onClick={copy}
          className="codeblock-copy"
          aria-label={t.nav.copy}
        >
          {copied ? (
            <>
              <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M3 8.5l3.2 3L13 4.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>{t.nav.copied}</span>
            </>
          ) : (
            <>
              <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" />
                <path d="M10.5 3.5v-1a1.5 1.5 0 0 0-1.5-1.5H4A1.5 1.5 0 0 0 2.5 2.5V9A1.5 1.5 0 0 0 4 10.5h1" strokeLinecap="round" />
              </svg>
              <span>{t.nav.copy}</span>
            </>
          )}
        </button>
      </div>
      <pre className="codeblock-pre">
        <code>
          {tokens.map((tok, i) =>
            tok.type === 'plain' ? (
              <span key={i}>{tok.value}</span>
            ) : (
              <span key={i} className={`tok-${tok.type}`}>
                {tok.value}
              </span>
            ),
          )}
        </code>
      </pre>
    </div>
  )
}

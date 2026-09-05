import { useEffect, useState } from 'react'
import { useLang } from '@/docs'

interface Props {
  headings: { id: string; text: string }[]
}

export function Toc({ headings }: Props) {
  const { t } = useLang()
  const [active, setActive] = useState<string>('')

  useEffect(() => {
    setActive('')
    if (!headings.length) return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(e.target.id)
        }
      },
      { rootMargin: '-80px 0px -70% 0px' },
    )
    headings.forEach((h) => {
      const el = document.getElementById(h.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [headings])

  if (!headings.length) return null

  return (
    <div className="toc">
      <div className="toc-title">{t.nav.onThisPage}</div>
      {headings.map((h) => (
        <a
          key={h.id}
          href={`#${h.id}`}
          className={`toc-link ${active === h.id ? 'toc-link-active' : ''}`}
          onClick={(e) => {
            e.preventDefault()
            document.getElementById(h.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }}
        >
          {h.text}
        </a>
      ))}
    </div>
  )
}

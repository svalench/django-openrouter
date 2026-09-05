import { useLang } from '@/docs'

interface Props {
  active: string
  onNavigate: (id: string) => void
}

export function Sidebar({ active, onNavigate }: Props) {
  const { t } = useLang()

  const groups: { name: string; ids: string[] }[] = []
  for (const s of t.sections) {
    const g = groups.find((x) => x.name === s.group)
    if (g) g.ids.push(s.id)
    else groups.push({ name: s.group, ids: [s.id] })
  }

  return (
    <nav className="sidebar-nav" aria-label="Docs">
      {groups.map((g) => (
        <div key={g.name} className="sidebar-group">
          <div className="sidebar-group-title">{g.name}</div>
          {g.ids.map((id) => {
            const s = t.sections.find((x) => x.id === id)!
            const isActive = active === id
            return (
              <button
                key={id}
                type="button"
                onClick={() => onNavigate(id)}
                className={`sidebar-link ${isActive ? 'sidebar-link-active' : ''}`}
              >
                <span className="sidebar-link-bar" aria-hidden />
                {s.title}
              </button>
            )
          })}
        </div>
      ))}
    </nav>
  )
}

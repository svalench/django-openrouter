import type { ReactElement } from 'react'
import type { Block, CalloutKind } from '@/docs/types'
import { CodeBlock } from './CodeBlock'
import { RichText } from './RichText'

const CALLOUT_STYLE: Record<CalloutKind, { cls: string; icon: ReactElement }> = {
  info: {
    cls: 'callout-info',
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4">
        <circle cx="8" cy="8" r="6.5" />
        <path d="M8 7.5V11M8 5.2v.2" strokeLinecap="round" />
      </svg>
    ),
  },
  tip: {
    cls: 'callout-tip',
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4">
        <path d="M8 1.5l1.8 3.9 4.2.5-3.1 2.9.8 4.2L8 11l-3.7 2 .8-4.2L2 5.9l4.2-.5L8 1.5z" strokeLinejoin="round" />
      </svg>
    ),
  },
  warning: {
    cls: 'callout-warning',
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4">
        <path d="M8 2L14.5 13h-13L8 2z" strokeLinejoin="round" />
        <path d="M8 6.5v3M8 11.2v.2" strokeLinecap="round" />
      </svg>
    ),
  },
  danger: {
    cls: 'callout-danger',
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4">
        <circle cx="8" cy="8" r="6.5" />
        <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" strokeLinecap="round" />
      </svg>
    ),
  },
}

export function Blocks({ blocks }: { blocks: Block[] }) {
  let h3Index = 0
  return (
    <div className="doc-blocks">
      {blocks.map((block, i) => {
        switch (block.type) {
          case 'p':
            return (
              <p key={i} className="doc-p">
                <RichText text={block.text} />
              </p>
            )
          case 'h3': {
            const id = `h-${h3Index++}`
            return (
              <h3 key={i} id={id} className="doc-h3 group">
                <a href={`#${id}`} className="doc-h3-anchor" aria-hidden>
                  #
                </a>
                {block.text}
              </h3>
            )
          }
          case 'code':
            return <CodeBlock key={i} lang={block.lang} code={block.code} title={block.title} />
          case 'list':
            return block.ordered ? (
              <ol key={i} className="doc-list doc-list-ol">
                {block.items.map((item, j) => (
                  <li key={j}>
                    <RichText text={item} />
                  </li>
                ))}
              </ol>
            ) : (
              <ul key={i} className="doc-list doc-list-ul">
                {block.items.map((item, j) => (
                  <li key={j}>
                    <RichText text={item} />
                  </li>
                ))}
              </ul>
            )
          case 'table':
            return (
              <div key={i} className="doc-table-wrap">
                <table className="doc-table">
                  <thead>
                    <tr>
                      {block.head.map((h, j) => (
                        <th key={j}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, j) => (
                      <tr key={j}>
                        {row.map((cell, k) => (
                          <td key={k}>
                            <RichText text={cell} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          case 'callout': {
            const style = CALLOUT_STYLE[block.kind]
            return (
              <aside key={i} className={`callout ${style.cls}`}>
                <span className="callout-icon">{style.icon}</span>
                <div>
                  {block.title && <div className="callout-title">{block.title}</div>}
                  <div className="callout-text">
                    <RichText text={block.text} />
                  </div>
                </div>
              </aside>
            )
          }
          case 'image':
            return (
              <figure key={i} className="doc-figure">
                <a href={block.src} target="_blank" rel="noreferrer" className="doc-figure-link">
                  <img src={block.src} alt={block.alt} loading="lazy" />
                </a>
                {block.caption && (
                  <figcaption className="doc-figure-caption">
                    <RichText text={block.caption} />
                  </figcaption>
                )}
              </figure>
            )
          case 'steps':
            return (
              <div key={i} className="doc-steps">
                {block.items.map((step, j) => (
                  <div key={j} className="doc-step">
                    <div className="doc-step-num">{j + 1}</div>
                    <div>
                      <div className="doc-step-title">{step.title}</div>
                      <div className="doc-step-text">
                        <RichText text={step.text} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )
          default:
            return null
        }
      })}
    </div>
  )
}

export function sectionHeadings(blocks: Block[]): { id: string; text: string }[] {
  let idx = 0
  return blocks
    .filter((b): b is Extract<Block, { type: 'h3' }> => b.type === 'h3')
    .map((b) => ({ id: `h-${idx++}`, text: b.text }))
}

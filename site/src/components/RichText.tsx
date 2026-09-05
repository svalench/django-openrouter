import { Fragment, type ReactNode } from 'react'

/** Renders inline `code` and **bold** markers from doc strings. */
export function RichText({ text }: { text: string }) {
  const parts: ReactNode[] = []
  // split by inline code first
  const codeSplit = text.split(/(`[^`]+`)/g)
  codeSplit.forEach((chunk, ci) => {
    if (chunk.startsWith('`') && chunk.endsWith('`') && chunk.length > 1) {
      parts.push(
        <code key={ci} className="inline-code">
          {chunk.slice(1, -1)}
        </code>,
      )
      return
    }
    const boldSplit = chunk.split(/(\*\*[^*]+\*\*)/g)
    boldSplit.forEach((piece, bi) => {
      if (piece.startsWith('**') && piece.endsWith('**') && piece.length > 4) {
        parts.push(
          <strong key={`${ci}-${bi}`} className="font-semibold text-foreground">
            {piece.slice(2, -2)}
          </strong>,
        )
      } else if (piece) {
        parts.push(<Fragment key={`${ci}-${bi}`}>{piece}</Fragment>)
      }
    })
  })
  return <>{parts}</>
}

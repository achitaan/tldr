import { useMemo } from 'react'
import { splitMath, typesetMath } from '../lib/math'

export function MathText({ text, className = '' }: { text: string; className?: string }) {
  const parts = useMemo(() => splitMath(text).map((part) => ({ part, html: part.kind === 'math' ? typesetMath(part.tex, part.display) : undefined })), [text])
  return <span className={`math-text ${className}`}>{parts.map(({ part, html }, index) => part.kind === 'text'
    ? part.raw
    : html
      ? <span key={index} className={part.display ? 'math-display' : 'math-inline'} title={part.tex} dangerouslySetInnerHTML={{ __html: html }} />
      : <span key={index} className="math-invalid" title="This expression could not be typeset; its original LaTeX is preserved.">{part.raw}</span>)}</span>
}

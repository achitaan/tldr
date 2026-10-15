import katex from 'katex'

export type MathPart = { kind: 'text'; raw: string } | { kind: 'math'; raw: string; tex: string; display: boolean }
const MAX_FORMULA = 4000
const MAX_ATTEMPTS = 128

/** Recognize explicit math without treating currency or code as an equation. */
export function splitMath(text: string): MathPart[] {
  const parts: MathPart[] = []
  let position = 0
  let start = 0
  let attempts = 0
  while (position < text.length && attempts < MAX_ATTEMPTS) {
    if (text[position] === '`') {
      const run = text.slice(position).match(/^`+/)?.[0] ?? '`'
      const end = text.indexOf(run, position + run.length)
      position = end < 0 ? text.length : end + run.length
      continue
    }
    const opener = text.startsWith('\\[', position) ? '\\[' : text.startsWith('\\(', position) ? '\\('
      : text.startsWith('$$', position) ? '$$' : text[position] === '$' && position + 1 < text.length && !/\s/.test(text[position + 1]) ? '$' : undefined
    if (!opener) {
      position += text[position] === '\\' ? 2 : 1
      continue
    }
    attempts++
    const display = opener === '$$' || opener === '\\['
    const closer = opener === '\\[' ? '\\]' : opener === '\\(' ? '\\)' : opener
    let end = position + opener.length
    const limit = Math.min(text.length, end + MAX_FORMULA + closer.length)
    for (; end < limit; end++) {
      if (text.startsWith(closer, end)) {
        if (opener !== '$' || (!/\s/.test(text[end - 1] ?? '') && !/\d/.test(text[end + 1] ?? ''))) break
        end = limit; break
      }
      if (!display && text[end] === '\n') { end = limit; break }
      if (text[end] === '\\') end++
    }
    if (end < limit && text.startsWith(closer, end) && text.slice(position + opener.length, end).trim()) {
      if (position > start) parts.push({ kind: 'text', raw: text.slice(start, position) })
      const stop = end + closer.length
      parts.push({ kind: 'math', raw: text.slice(position, stop), tex: text.slice(position + opener.length, end), display })
      position = stop
      start = stop
    } else position += opener.length
  }
  if (start < text.length) parts.push({ kind: 'text', raw: text.slice(start) })
  return parts
}

/** Only KaTeX output enters the DOM. Inputs and parse errors remain text. */
export function typesetMath(tex: string, display: boolean): string | undefined {
  if (!tex.trim() || tex.length > MAX_FORMULA) return undefined
  try {
    // Presentation-only compatibility for extracted notes. Keep saved/source TeX
    // unchanged; unresolved cross-references still fall back instead of inventing numbers.
    const notation = tex.replace(/\\mbox\b/g, '\\text').replace(/\\label\{[A-Za-z0-9:._-]{1,120}\}/g, '')
    return katex.renderToString(notation, {
      displayMode: display, output: 'htmlAndMathml', throwOnError: true,
      trust: false, strict: 'error', maxExpand: 500, maxSize: 10,
      macros: {}, // Definitions cannot leak into another expression or course.
    })
  } catch {
    return undefined
  }
}

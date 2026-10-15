import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { MathText } from '../components/MathText'
import { splitMath, typesetMath } from './math'

describe('local LaTeX typesetting', () => {
  it('recognizes inline and display delimiters and preserves original text', () => {
    const source = String.raw`Use \(x^2\), $2+2=4$, then \[\frac{1}{2}\] and $$\sum_{i=1}^n i$$.`
    const parts = splitMath(source)
    expect(parts.map((p) => p.raw).join('')).toBe(source)
    expect(parts.filter((p) => p.kind === 'math').map((p) => p.display)).toEqual([false, false, true, true])
  })
  it('leaves currency, escaped dollars and code literal', () => {
    for (const text of [String.raw`Pay $20 per month or $10 per week.`, String.raw`A \$5 cost.`, '`$x^2$`', '```\n$y$\n```']) {
      expect(splitMath(text)).toEqual([{ kind: 'text', raw: text }])
    }
    expect(splitMath('Price $20; use $x^2$ next.').filter((p) => p.kind === 'math')).toHaveLength(1)
  })
  it('renders fractions and matrices with accessible MathML', () => {
    const html = renderToStaticMarkup(<MathText text={String.raw`\[\frac{dy}{dx}=\begin{bmatrix}1&2\\3&4\end{bmatrix}\]`} />)
    expect(html).toContain('<math')
    expect(html).toContain('<mfrac>')
    expect(html).toContain('<mtable')
    expect(html).toContain('application/x-tex')
  })
  it('preserves invalid expressions and bounds expansion', () => {
    const broken = String.raw`\(\frac{1}{\)`
    expect(renderToStaticMarkup(<MathText text={broken} />)).toContain('math-invalid')
    expect(typesetMath(String.raw`\def\loop{\loop}\loop`, false)).toBeUndefined()
    expect(typesetMath('x'.repeat(4001), false)).toBeUndefined()
    const text = String.raw`\(x`.repeat(5000)
    expect(splitMath(text).map((p) => p.raw).join('')).toBe(text)
  })
  it('previews extracted equation labels and text boxes without changing source or inventing references', () => {
    const source = String.raw`\[\begin{equation}f'(x)=\lim_{h\to0}\frac{f(x+h)-f(x)}{h}\label{eq:eq2}\end{equation}\]`
    const parts = splitMath(source)
    expect(parts.map((part) => part.raw).join('')).toBe(source)
    expect(renderToStaticMarkup(<MathText text={source} />)).toContain('<mfrac>')
    expect(typesetMath(String.raw`\begin{array}{lr}h&\mbox{if }h\ge0\\-h&\mbox{if }h<0\end{array}`, true)).toContain('<mtable')
    expect(typesetMath(String.raw`\eqref{eq:eq2}`, false)).toBeUndefined()
    expect(typesetMath(String.raw`\label{\href{javascript:alert(1)}{x}}`, true)).toBeUndefined()
  })
  it('does not inject HTML or enable trusted commands or shared macros', () => {
    const html = renderToStaticMarkup(<MathText text={String.raw`<img src=x onerror=alert(1)> \(\href{javascript:alert(1)}{click}\) \(\includegraphics{https://example.com/x}\)`} />)
    expect(html).not.toMatch(/<(img|a|script)\b/)
    expect(html).toContain('&lt;img')
    typesetMath(String.raw`\gdef\shared{123}\shared`, false)
    expect(typesetMath(String.raw`\shared`, false)).toBeUndefined()
  })
})

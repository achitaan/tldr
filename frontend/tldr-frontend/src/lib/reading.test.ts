import { describe, expect, it } from 'vitest'
import { readingBlocks } from './reading'

describe('source reading presentation', () => {
  it('keeps blank lines inside display math intact', () => {
    const equation = String.raw`\[
\begin{aligned}
x &= 1 \\

y &= 2
\end{aligned}
\]`
    expect(readingBlocks(`Before.\n\n${equation}\n\nAfter.`)).toEqual(['Before.', equation, 'After.'])
  })

  it('preserves inline math and heading text while removing excess paragraph gaps', () => {
    expect(readingBlocks('## Speed\r\n\r\n\r\nUse \\(x = vt\\).\r\n\r\nNext.'))
      .toEqual(['## Speed', 'Use \\(x = vt\\).', 'Next.'])
  })
})

import { splitMath } from './math'

/** Format source paragraphs without splitting a recognized multiline formula. */
export function readingBlocks(text: string): string[] {
  const blocks: string[] = []
  let current = ''
  for (const part of splitMath(text.replace(/\r\n/g, '\n'))) {
    if (part.kind === 'math') {
      current += part.raw
      continue
    }
    const paragraphs = part.raw.split(/\n[\t ]*\n(?:[\t ]*\n)*/)
    current += paragraphs[0]
    for (const paragraph of paragraphs.slice(1)) {
      if (current.trim()) blocks.push(current.trim())
      current = paragraph
    }
  }
  if (current.trim()) blocks.push(current.trim())
  return blocks
}

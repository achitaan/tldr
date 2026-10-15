/** Preserve actual coordinates, including values outside the unit interval. */
export function plotPath(points: number[][]): string | undefined {
  if (points.length < 2 || points.some((point) => point.length !== 2 || !point.every(Number.isFinite))) return undefined
  const xs = points.map((point) => point[0]), ys = points.map((point) => point[1])
  const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys)
  const dx = xmax - xmin, dy = ymax - ymin
  if (!Number.isFinite(dx) || !Number.isFinite(dy)) return undefined
  return points.map(([x, y], index) => `${index ? 'L' : 'M'} ${18 + (dx ? (x - xmin) / dx : .5) * 184} ${88 - (dy ? (y - ymin) / dy : .5) * 58}`).join(' ')
}

export function timingPath(values: Array<0 | 1>, baseline: number): string {
  if (!values.length) return ''
  const width = 132 / values.length
  return values.map((value, index) => `${index ? `V ${baseline - value * 12}` : `M 72 ${baseline - value * 12}`} H ${72 + (index + 1) * width}`).join(' ')
}

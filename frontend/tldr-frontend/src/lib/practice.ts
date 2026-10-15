import type { PracticeCheckpoint } from '../types'

export function crossedPractice(points: PracticeCheckpoint[], previous: number, current: number, seen: ReadonlySet<string>) {
  if (!Number.isFinite(previous) || !Number.isFinite(current) || current <= previous) return undefined
  return points.filter((point) => Number.isFinite(point.time_seconds) && point.time_seconds >= 0 && !seen.has(point.id) && point.time_seconds > previous && point.time_seconds <= current)
    .sort((a, b) => a.time_seconds - b.time_seconds)[0]
}

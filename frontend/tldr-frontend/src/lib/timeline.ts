export type TimedScene = { start_seconds?: number; end_seconds?: number }

// Browser media clocks and JSON floating points differ below a millisecond.
// Use the same millisecond intervals as the backend context validator.
export function timelineSeconds(seconds: number): number {
  return Math.round(seconds * 1000) / 1000
}

export function sceneAtTime<T extends TimedScene>(scenes: T[], seconds: number, duration: number): T | undefined {
  if (!Number.isFinite(seconds)) return undefined
  const time = timelineSeconds(seconds)
  const match = scenes.find((scene) => time >= timelineSeconds(scene.start_seconds ?? 0) && time < timelineSeconds(scene.end_seconds ?? duration))
  const last = scenes[scenes.length - 1]
  return match ?? (last && time >= timelineSeconds(last.start_seconds ?? 0) && time <= timelineSeconds(duration) ? last : undefined)
}

export function sceneSeekTime(scene: TimedScene, duration: number): number {
  const start = timelineSeconds(scene.start_seconds ?? 0)
  const end = timelineSeconds(scene.end_seconds ?? duration)
  return start + Math.min(.02, Math.max(0, end - start) / 4)
}

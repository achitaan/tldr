import { describe, expect, it } from 'vitest'
import {
  clientToNormalized,
  normalizedRect,
  rotatedToSource,
  sourceToRotated,
  type Rotation,
} from './geometry'

describe('page region coordinate transforms', () => {
  const width = 800
  const height = 1000

  it.each<Rotation>([0, 90, 180, 270])(
    'round trips points at %s degrees',
    (rotation) => {
      const original = { x: 234, y: 731 }
      const rotated = sourceToRotated(original, width, height, rotation)
      expect(rotatedToSource(rotated, width, height, rotation)).toEqual(original)
    },
  )

  it('maps a client point through a 90 degree rotated SVG', () => {
    const point = clientToNormalized(
      { x: 150, y: 40 },
      { left: 50, top: 40, width: 500, height: 400 },
      width,
      height,
      90,
    )
    expect(point.x).toBeCloseTo(0)
    expect(point.y).toBeCloseTo(0.8)
  })

  it('normalizes reverse-direction region drags', () => {
    const rect = normalizedRect({ x: 0.7, y: 0.8 }, { x: 0.2, y: 0.3 })
    expect(rect.x).toBeCloseTo(0.2)
    expect(rect.y).toBeCloseTo(0.3)
    expect(rect.width).toBeCloseTo(0.5)
    expect(rect.height).toBeCloseTo(0.5)
  })
})

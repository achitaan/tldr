import { describe, expect, it } from 'vitest'
import { crossedPractice } from './practice'

const points = [20, 10].map((time) => ({ id: String(time), scene_id: 'scene', time_seconds: time, question: 'Predict?', answer: 'Reason.' }))

describe('practice checkpoints', () => {
  it('pauses on the earliest unseen point actually crossed during playback', () => {
    expect(crossedPractice(points, 9.8, 10.1, new Set())?.id).toBe('10')
    expect(crossedPractice(points, 9, 21, new Set())?.id).toBe('10')
    expect(crossedPractice(points, 9, 21, new Set(['10']))?.id).toBe('20')
  })
  it('does not pause again after reset-to-checkpoint, backward seeking or invalid clocks', () => {
    expect(crossedPractice(points, 10, 10.5, new Set())).toBeUndefined()
    expect(crossedPractice(points, 21, 9, new Set())).toBeUndefined()
    expect(crossedPractice(points, NaN, 11, new Set())).toBeUndefined()
    expect(crossedPractice(points, 9, 11, new Set(['10']))).toBeUndefined()
  })
})

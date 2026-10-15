import { describe, expect, it } from 'vitest'
import { sceneAtTime, sceneSeekTime } from './timeline'

describe('media clock scene boundaries', () => {
  const before = { id: 'early', start_seconds: 59.1, end_seconds: 74.99999999999987 }
  const after = { id: 'ready', start_seconds: 74.99999999999987, end_seconds: 91.873 }
  it('keeps a browser-rounded chapter seek in the selected scene', () => {
    expect(sceneAtTime([before, after], 74.999999, 91.873)?.id).toBe('ready')
    expect(sceneAtTime([before, after], sceneSeekTime(after, 91.873), 91.873)?.id).toBe('ready')
    expect(sceneAtTime([before, after], 74.98, 91.873)?.id).toBe('early')
  })
  it('captures the final scene at video end and rejects nonfinite positions', () => {
    expect(sceneAtTime([before, after], 91.873, 91.873)?.id).toBe('ready')
    expect(sceneAtTime([before, after], NaN, 91.873)).toBeUndefined()
  })
})

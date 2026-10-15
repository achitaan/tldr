import { describe, expect, it } from 'vitest'
import { plotPath, timingPath } from './preview'

describe('faithful schematic previews', () => {
  it('retains relative growth for financial values outside zero to one', () => {
    expect(plotPath([[0, 1000], [1, 1050], [2, 1100]])).toBe('M 18 88 L 110 59 L 202 30')
    expect(plotPath([])).toBeUndefined()
    expect(plotPath([[0, 1], [1, Infinity]])).toBeUndefined()
  })
  it('uses digital steps instead of interpolated ramps on a common time axis', () => {
    expect(timingPath([0, 1, 1, 0], 30)).toBe('M 72 30 H 105 V 18 H 138 V 18 H 171 V 30 H 204')
    expect(timingPath([1, 0, 0, 1], 56)).toBe('M 72 44 H 105 V 56 H 138 V 56 H 171 V 44 H 204')
  })
})

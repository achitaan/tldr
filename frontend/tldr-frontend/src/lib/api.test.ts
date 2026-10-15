import { describe, expect, it } from 'vitest'
import { formatApiError } from './api'

describe('API validation errors', () => {
  it('keeps teaching-plan paths and messages readable for nested DRF errors', () => {
    expect(formatApiError({
      teaching_plan: [
        { path: 'goals[0].requires[1]', message: 'Unknown prerequisite id.' },
        { path: 'scenes[2].evidence[0].fingerprint', message: 'Evidence fingerprint is stale.' },
      ],
    })).toBe('goals[0].requires[1]: Unknown prerequisite id. scenes[2].evidence[0].fingerprint: Evidence fingerprint is stale.')
  })

  it('falls back to nested field names when a structured path is absent', () => {
    expect(formatApiError({ teaching_plan: { version: ['Must be 1.'] } })).toBe('teaching_plan.version: Must be 1.')
  })
})

import { describe, expect, it } from 'vitest'
import type { LessonRevision, LessonSpec, TeachingPlan, TeachingPlanReport } from '../types'
import {
  emptyTeachingPlan,
  matchesSavedRevision,
  teachingCoverageRows,
  teachingPlanForRevision,
  teachingPlanValidationKey,
  validationIsCurrent,
  validationRequest,
} from './teachingPlan'

const spec: LessonSpec = {
  title: 'Evidence lesson',
  target_minutes: 10,
  chapters: [{ id: 'chapter-1', title: 'Start', scenes: [{ id: 'scene-1', title: 'Claim', narration: 'Explain it.', source_refs: ['r7'], objects: [] }] }],
}

const plan: TeachingPlan = {
  version: 1,
  goals: [{ id: 'goal-1', text: 'Explain the claim.', requires: ['assumption-1'] }],
  assumed_prerequisites: [{ id: 'assumption-1', text: 'Read a graph.' }],
  scenes: [{
    scene_id: 'scene-1',
    goal_ids: ['goal-1'],
    evidence: [{ source_ref: 'r7', fingerprint: 'sha256:current-source-fingerprint' }],
    visual_requests: [{ object_id: 'claim-line', kind: 'line', purpose: 'Make the comparison visible.' }],
    checks: [{ id: 'check-1', goal_ids: ['goal-1'], question: 'What changes?', expected_reasoning: 'Compare the two states.' }],
  }],
}

const revision = (teaching_plan: TeachingPlan | null | undefined): LessonRevision => ({
  id: 9,
  lesson: 3,
  number: 2,
  spec,
  citations: [],
  ...(teaching_plan === undefined ? {} : { teaching_plan }),
})

describe('teaching plan draft boundaries', () => {
  it('creates an explicit empty v1 plan without inferred goals or scene records', () => {
    expect(emptyTeachingPlan()).toEqual({ version: 1, goals: [], assumed_prerequisites: [], scenes: [] })
  })

  it('preserves IDs, check links, and evidence fingerprints during request serialization', () => {
    const payload = validationRequest(revision(null), spec, plan)
    expect(payload).toEqual({ spec, teaching_plan: plan })
    expect(JSON.parse(JSON.stringify(payload))).toEqual({ spec, teaching_plan: plan })
  })

  it('treats omitted and null legacy plans as no saved plan', () => {
    expect(teachingPlanForRevision(revision(undefined))).toBeNull()
    expect(teachingPlanForRevision(revision(null))).toBeNull()
    expect(validationRequest(revision(null), spec, null)).toEqual({ revision_id: 9 })
  })

  it('uses a saved revision request only while both storyboard and plan are unchanged', () => {
    const saved = revision(plan)
    expect(matchesSavedRevision(spec, plan, saved)).toBe(true)
    expect(validationRequest(saved, spec, plan)).toEqual({ revision_id: 9 })
    expect(validationRequest({ ...saved, spec: { ...spec, chapters: [{ ...spec.chapters[0], start_seconds: 0, end_seconds: 12 }] } }, spec, plan)).toEqual({ revision_id: 9 })
    expect(validationRequest(saved, { ...spec, title: 'Edited' }, plan)).toHaveProperty('spec')
    expect(validationRequest(saved, spec, { ...plan, goals: [{ ...plan.goals[0], text: 'Edited' }] })).toHaveProperty('teaching_plan')
  })

  it('keeps planned checks distinct from installed manifest checkpoints', () => {
    const report: TeachingPlanReport = {
      plan_status: 'complete',
      can_save: true,
      issues: [],
      coverage: [{ goal_id: 'goal-1', explanation_scene_ids: ['scene-1'], planned_check_ids: ['check-1'], installed_practice_ids: ['practice-9'] }],
      evidence_bindings: [],
      media_status: 'saved_revision',
    }
    expect(teachingCoverageRows(plan, report)).toEqual([{
      goal_id: 'goal-1',
      goalText: 'Explain the claim.',
      explanation_scene_ids: ['scene-1'],
      planned_check_ids: ['check-1'],
      installed_practice_ids: ['practice-9'],
    }])
  })

  it('invalidates reports and late responses across edits, revisions, and courses', () => {
    const original = teachingPlanValidationKey(1, 9, spec, plan)
    expect(validationIsCurrent({ run: 1, scope: original }, { run: 1, scope: original })).toBe(true)
    expect(validationIsCurrent({ run: 1, scope: original }, { run: 1, scope: teachingPlanValidationKey(1, 9, { ...spec, title: 'Edited' }, plan) })).toBe(false)
    expect(validationIsCurrent({ run: 1, scope: original }, { run: 1, scope: teachingPlanValidationKey(1, 10, spec, plan) })).toBe(false)
    expect(validationIsCurrent({ run: 1, scope: original }, { run: 1, scope: teachingPlanValidationKey(2, 9, spec, plan) })).toBe(false)
  })

  it('keeps a newer report when an older request returns after away-and-back edits', () => {
    const scopeX = teachingPlanValidationKey(1, 9, spec, plan)
    const scopeY = teachingPlanValidationKey(1, 9, { ...spec, title: 'Temporary edit' }, plan)
    const requestA = { run: 1, scope: scopeX }
    const requestDuringEdit = { run: 2, scope: scopeY }
    const requestB = { run: 3, scope: scopeX }
    const current = requestB
    let displayedReport = 'none'
    const accept = (request: typeof requestA, report: string) => {
      if (validationIsCurrent(request, current)) displayedReport = report
    }

    expect(validationIsCurrent(requestDuringEdit, current)).toBe(false)
    accept(requestB, 'fresh B')
    accept(requestA, 'stale A')
    expect(displayedReport).toBe('fresh B')
  })
})

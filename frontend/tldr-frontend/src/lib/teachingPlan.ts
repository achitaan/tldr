import type {
  Course,
  LessonRevision,
  LessonSpec,
  TeachingGoalCoverage,
  TeachingPlan,
  TeachingPlanReport,
} from '../types'
import { rendererSpec } from './lesson'

export function emptyTeachingPlan(): TeachingPlan {
  return {
    version: 1,
    goals: [],
    assumed_prerequisites: [],
    scenes: [],
  }
}

export function teachingPlanForRevision(revision?: LessonRevision): TeachingPlan | null {
  return revision?.teaching_plan ?? null
}

export function nextTeachingId(prefix: string, existing: string[]): string {
  const used = new Set(existing)
  let index = 1
  while (used.has(`${prefix}-${index}`)) index += 1
  return `${prefix}-${index}`
}

export function teachingPlanValidationKey(
  courseId: Course['id'],
  revisionId: LessonRevision['id'] | undefined,
  spec: LessonSpec,
  plan: TeachingPlan | null,
): string {
  return stableSerialize([String(courseId), revisionId === undefined ? null : String(revisionId), spec, plan])
}

export function matchesSavedRevision(spec: LessonSpec, plan: TeachingPlan | null, revision?: LessonRevision): boolean {
  return Boolean(revision)
    && stableSerialize(rendererSpec(spec)) === stableSerialize(revision ? rendererSpec(revision.spec) : undefined)
    && stableSerialize(plan) === stableSerialize(teachingPlanForRevision(revision))
}

export function validationRequest(
  revision: LessonRevision,
  spec: LessonSpec,
  plan: TeachingPlan | null,
): { revision_id: LessonRevision['id'] } | { spec: LessonSpec; teaching_plan: TeachingPlan | null } {
  return matchesSavedRevision(spec, plan, revision)
    ? { revision_id: revision.id }
    : { spec, teaching_plan: plan }
}

export type TeachingValidationToken = {
  run: number
  scope: string
}

export function validationIsCurrent(request: TeachingValidationToken, current: TeachingValidationToken): boolean {
  return request.run === current.run && request.scope === current.scope
}

export type TeachingCoverageRow = TeachingGoalCoverage & {
  goalText: string
}

export function teachingCoverageRows(plan: TeachingPlan | null, report: TeachingPlanReport | null): TeachingCoverageRow[] {
  if (!plan) return []
  return plan.goals.map((goal) => {
    const coverage = report?.coverage.find((entry) => entry.goal_id === goal.id)
    return {
      goal_id: goal.id,
      goalText: goal.text,
      explanation_scene_ids: coverage?.explanation_scene_ids ?? [],
      planned_check_ids: coverage?.planned_check_ids ?? [],
      installed_practice_ids: coverage?.installed_practice_ids ?? [],
    }
  })
}

function stableSerialize(value: unknown): string {
  return JSON.stringify(value, (_key, entry) => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) return entry
    return Object.fromEntries(Object.entries(entry as Record<string, unknown>).sort(([left], [right]) => left.localeCompare(right)))
  })
}

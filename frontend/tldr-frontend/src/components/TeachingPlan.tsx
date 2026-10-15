import type { LessonRevision, LessonSpec, TeachingPlan as TeachingPlanValue, TeachingPlanReport, TeachingScenePlan } from '../types'
import { nextTeachingId, teachingCoverageRows } from '../lib/teachingPlan'

type Props = {
  revision: LessonRevision
  spec: LessonSpec
  plan: TeachingPlanValue | null
  report: TeachingPlanReport | null
  validating: boolean
  demo: boolean
  onCreate: () => void
  onChange: (plan: TeachingPlanValue) => void
  onValidate: () => void
}

export function TeachingPlan({ revision, spec, plan, report, validating, demo, onCreate, onChange, onValidate }: Props) {
  const scenes = spec.chapters.flatMap((chapter) => chapter.scenes.map((scene) => ({ ...scene, chapterTitle: chapter.title })))

  if (!plan) {
    return (
      <section className="teaching-plan-panel" aria-labelledby="teaching-plan-title">
        <div className="teaching-plan-heading">
          <div>
            <span className="quiet-label">Teaching plan</span>
            <h2 id="teaching-plan-title">No teaching plan saved</h2>
            <p>Inspect this saved revision for structural findings, or explicitly create a plan for a new revision. Validation does not modify the lesson.</p>
          </div>
          <div className="button-row">
            {report && <span className={`status-tag teaching-status ${report.plan_status}`}>{report.plan_status}</span>}
            <button className="button" type="button" onClick={onValidate} disabled={validating || demo}>{validating ? 'Checking' : 'Validate coverage'}</button>
            <button className="button" type="button" onClick={onCreate}>Create teaching plan</button>
          </div>
        </div>
        {demo && <p className="inline-note">Coverage validation is available in the local app. This static demo makes no network requests.</p>}
        <TeachingValidationReport plan={null} report={report} />
      </section>
    )
  }

  const updateScenePlan = (sceneId: string, update: (scene: TeachingScenePlan) => TeachingScenePlan) => {
    const existing = plan.scenes.find((scene) => scene.scene_id === sceneId) ?? {
      scene_id: sceneId,
      goal_ids: [],
      evidence: [],
      visual_requests: [],
      checks: [],
    }
    const next = update(existing)
    onChange({
      ...plan,
      scenes: plan.scenes.some((scene) => scene.scene_id === sceneId)
        ? plan.scenes.map((scene) => scene.scene_id === sceneId ? next : scene)
        : [...plan.scenes, next],
    })
  }

  const removeGoal = (goalId: string) => onChange({
    ...plan,
    goals: plan.goals.filter((goal) => goal.id !== goalId).map((goal) => ({ ...goal, requires: goal.requires.filter((id) => id !== goalId) })),
    scenes: plan.scenes.map((scene) => ({
      ...scene,
      goal_ids: scene.goal_ids.filter((id) => id !== goalId),
      checks: scene.checks.map((check) => ({ ...check, goal_ids: check.goal_ids.filter((id) => id !== goalId) })),
    })),
  })

  const currentFingerprint = (sourceRef: string) => report?.evidence_bindings.find((entry) => entry.source_ref === sourceRef)?.fingerprint
  return (
    <section className="teaching-plan-panel" aria-labelledby="teaching-plan-title">
      <div className="teaching-plan-heading">
        <div>
          <span className="quiet-label">Teaching plan · revision {revision.number}</span>
          <h2 id="teaching-plan-title">Structural teaching coverage</h2>
          <p>Plan what each scene explains and checks. Validation reports structure and installed practice; it does not approve scientific correctness or learner mastery.</p>
        </div>
        <div className="button-row">
          {report && <span className={`status-tag teaching-status ${report.plan_status}`}>{report.plan_status}</span>}
          <button className="button" type="button" onClick={onValidate} disabled={validating || demo}>{validating ? 'Checking' : 'Validate coverage'}</button>
        </div>
      </div>

      {demo && <p className="inline-note">Coverage validation is available in the local app. This static demo makes no network requests.</p>}

      <details className="teaching-plan-section" open>
        <summary>Goals and prerequisites <span>{plan.goals.length} goal{plan.goals.length === 1 ? '' : 's'}</span></summary>
        <div className="teaching-plan-fields">
          {plan.goals.map((goal, goalIndex) => (
            <fieldset className="teaching-item" key={goal.id}>
              <legend>Goal {goalIndex + 1} · {goal.id}</legend>
              <label>Goal text<textarea rows={2} maxLength={600} value={goal.text} onChange={(event) => onChange({ ...plan, goals: plan.goals.map((entry) => entry.id === goal.id ? { ...entry, text: event.target.value } : entry) })} /></label>
              <fieldset className="teaching-link-picker">
                <legend>Requires</legend>
                {[...plan.goals.filter((entry) => entry.id !== goal.id).map((entry) => ({ id: entry.id, text: entry.text || entry.id })), ...plan.assumed_prerequisites.map((entry) => ({ id: entry.id, text: entry.text || entry.id }))].map((requirement) => (
                  <label key={requirement.id}><input type="checkbox" checked={goal.requires.includes(requirement.id)} onChange={() => onChange({ ...plan, goals: plan.goals.map((entry) => entry.id === goal.id ? { ...entry, requires: entry.requires.includes(requirement.id) ? entry.requires.filter((id) => id !== requirement.id) : [...entry.requires, requirement.id] } : entry) })} /> {requirement.text}</label>
                ))}
                {plan.goals.length + plan.assumed_prerequisites.length <= 1 && <small>Add another goal or an explicit prerequisite to create a dependency.</small>}
              </fieldset>
              <button className="text-button" type="button" onClick={() => removeGoal(goal.id)}>Remove goal</button>
            </fieldset>
          ))}
          <button className="button compact" type="button" disabled={plan.goals.length >= 40} onClick={() => onChange({ ...plan, goals: [...plan.goals, { id: nextTeachingId('goal', plan.goals.map((goal) => goal.id)), text: '', requires: [] }] })}>Add goal</button>

          {plan.assumed_prerequisites.map((assumption, assumptionIndex) => (
            <fieldset className="teaching-item" key={assumption.id}>
              <legend>Explicit prerequisite {assumptionIndex + 1} · {assumption.id}</legend>
              <label>Prerequisite text<input maxLength={600} value={assumption.text} onChange={(event) => onChange({ ...plan, assumed_prerequisites: plan.assumed_prerequisites.map((entry) => entry.id === assumption.id ? { ...entry, text: event.target.value } : entry) })} /></label>
              <button className="text-button" type="button" onClick={() => onChange({ ...plan, assumed_prerequisites: plan.assumed_prerequisites.filter((entry) => entry.id !== assumption.id), goals: plan.goals.map((goal) => ({ ...goal, requires: goal.requires.filter((id) => id !== assumption.id) })) })}>Remove prerequisite</button>
            </fieldset>
          ))}
          <button className="button compact" type="button" disabled={plan.assumed_prerequisites.length >= 40} onClick={() => onChange({ ...plan, assumed_prerequisites: [...plan.assumed_prerequisites, { id: nextTeachingId('assumption', plan.assumed_prerequisites.map((entry) => entry.id)), text: '' }] })}>Add prerequisite</button>
        </div>
      </details>

      <details className="teaching-plan-section">
        <summary>Scene coverage <span>{plan.scenes.length} of {scenes.length} planned</span></summary>
        <div className="teaching-scene-list">
          {scenes.map((scene) => {
            const scenePlan = plan.scenes.find((entry) => entry.scene_id === scene.id)
            return (
              <details className="teaching-scene" key={scene.id}>
                <summary><span>{scene.title}</span><small>{scene.chapterTitle} · {scene.id}</small></summary>
                <div className="teaching-plan-fields">
                  <fieldset className="teaching-link-picker">
                    <legend>Assigned goals</legend>
                    {plan.goals.map((goal) => <label key={goal.id}><input type="checkbox" checked={scenePlan?.goal_ids.includes(goal.id) ?? false} onChange={() => updateScenePlan(scene.id, (entry) => entry.goal_ids.includes(goal.id) ? { ...entry, goal_ids: entry.goal_ids.filter((id) => id !== goal.id), checks: entry.checks.map((check) => ({ ...check, goal_ids: check.goal_ids.filter((id) => id !== goal.id) })) } : { ...entry, goal_ids: [...entry.goal_ids, goal.id] })} /> {goal.text || goal.id}</label>)}
                    {plan.goals.length === 0 && <small>Add a goal before assigning this scene.</small>}
                  </fieldset>

                  <fieldset className="teaching-item">
                    <legend>Evidence bindings</legend>
                    {scene.source_refs.map((sourceRef) => {
                      const bound = scenePlan?.evidence.find((entry) => entry.source_ref === sourceRef)
                      const fingerprint = currentFingerprint(sourceRef)
                      return <div className="evidence-binding" key={sourceRef}><code>{sourceRef}</code><span>{bound ? 'Bound' : 'Not bound'}</span><button className="button compact" type="button" disabled={!fingerprint} title={fingerprint ? undefined : 'Validate coverage to load the current fingerprint.'} onClick={() => fingerprint && updateScenePlan(scene.id, (entry) => ({ ...entry, evidence: [...entry.evidence.filter((item) => item.source_ref !== sourceRef), { source_ref: sourceRef, fingerprint }] }))}>{bound ? 'Rebind current evidence' : 'Bind current evidence'}</button></div>
                    })}
                    {scene.source_refs.length === 0 && <small>This storyboard scene has no source references.</small>}
                    {(scenePlan?.evidence ?? []).filter((binding) => !scene.source_refs.includes(binding.source_ref)).map((binding) => <div className="evidence-binding stale" key={binding.source_ref}><code>{binding.source_ref}</code><span>Not in storyboard scene</span><button className="text-button" type="button" onClick={() => updateScenePlan(scene.id, (entry) => ({ ...entry, evidence: entry.evidence.filter((item) => item.source_ref !== binding.source_ref) }))}>Remove binding</button></div>)}
                  </fieldset>

                  <fieldset className="teaching-item">
                    <legend>Requested visual purposes</legend>
                    {(scenePlan?.visual_requests ?? []).map((request, requestIndex) => (
                      <div className="teaching-subitem" key={`${request.object_id}-${requestIndex}`}>
                        <label>Scene object<select value={request.object_id} onChange={(event) => { const object = scene.objects.find((entry) => entry.id === event.target.value); updateScenePlan(scene.id, (entry) => ({ ...entry, visual_requests: entry.visual_requests.map((item, index) => index === requestIndex ? { ...item, object_id: event.target.value, kind: object?.kind ?? item.kind } : item) })) }}>{scene.objects.map((object) => <option value={object.id} key={object.id}>{object.label} · {object.kind}</option>)}</select></label>
                        <label>Purpose<textarea rows={2} maxLength={600} value={request.purpose} onChange={(event) => updateScenePlan(scene.id, (entry) => ({ ...entry, visual_requests: entry.visual_requests.map((item, index) => index === requestIndex ? { ...item, purpose: event.target.value } : item) }))} /></label>
                        <button className="text-button" type="button" onClick={() => updateScenePlan(scene.id, (entry) => ({ ...entry, visual_requests: entry.visual_requests.filter((_, index) => index !== requestIndex) }))}>Remove visual request</button>
                      </div>
                    ))}
                    <button className="button compact" type="button" disabled={scene.objects.length === 0 || (scenePlan?.visual_requests.length ?? 0) >= Math.min(6, scene.objects.length)} onClick={() => { const object = scene.objects.find((candidate) => !scenePlan?.visual_requests.some((request) => request.object_id === candidate.id)); if (object) updateScenePlan(scene.id, (entry) => ({ ...entry, visual_requests: [...entry.visual_requests, { object_id: object.id, kind: object.kind, purpose: '' }] })) }}>Add visual purpose</button>
                  </fieldset>

                  <fieldset className="teaching-item">
                    <legend>Proposed checks</legend>
                    {(scenePlan?.checks ?? []).map((check, checkIndex) => (
                      <div className="teaching-subitem" key={check.id}>
                        <strong>Check {checkIndex + 1} · {check.id}</strong>
                        <fieldset className="teaching-link-picker"><legend>Checks goals</legend>{(scenePlan?.goal_ids ?? []).map((goalId) => { const goal = plan.goals.find((entry) => entry.id === goalId); return <label key={goalId}><input type="checkbox" checked={check.goal_ids.includes(goalId)} onChange={() => updateScenePlan(scene.id, (entry) => ({ ...entry, checks: entry.checks.map((item) => item.id === check.id ? { ...item, goal_ids: item.goal_ids.includes(goalId) ? item.goal_ids.filter((id) => id !== goalId) : [...item.goal_ids, goalId] } : item) }))} /> {goal?.text || goalId}</label> })}</fieldset>
                        <label>Question<textarea rows={2} maxLength={600} value={check.question} onChange={(event) => updateScenePlan(scene.id, (entry) => ({ ...entry, checks: entry.checks.map((item) => item.id === check.id ? { ...item, question: event.target.value } : item) }))} /></label>
                        <label>Expected reasoning<textarea rows={3} maxLength={2000} value={check.expected_reasoning} onChange={(event) => updateScenePlan(scene.id, (entry) => ({ ...entry, checks: entry.checks.map((item) => item.id === check.id ? { ...item, expected_reasoning: event.target.value } : item) }))} /></label>
                        <button className="text-button" type="button" onClick={() => updateScenePlan(scene.id, (entry) => ({ ...entry, checks: entry.checks.filter((item) => item.id !== check.id) }))}>Remove check</button>
                      </div>
                    ))}
                    <button className="button compact" type="button" disabled={(scenePlan?.checks.length ?? 0) >= 6} onClick={() => updateScenePlan(scene.id, (entry) => ({ ...entry, checks: [...entry.checks, { id: nextTeachingId('check', plan.scenes.flatMap((item) => item.checks.map((check) => check.id))), goal_ids: [], question: '', expected_reasoning: '' }] }))}>Add proposed check</button>
                    <small>Proposed checks are planning records. Installed practice comes only from a completed render manifest.</small>
                  </fieldset>
                </div>
              </details>
            )
          })}
          {plan.scenes.filter((scenePlan) => !scenes.some((scene) => scene.id === scenePlan.scene_id)).map((scenePlan) => <div className="teaching-item" key={scenePlan.scene_id}><strong>Unknown scene · {scenePlan.scene_id}</strong><small>This plan record no longer matches the storyboard.</small><button className="text-button" type="button" onClick={() => onChange({ ...plan, scenes: plan.scenes.filter((entry) => entry.scene_id !== scenePlan.scene_id) })}>Remove scene plan</button></div>)}
        </div>
      </details>

      <TeachingValidationReport plan={plan} report={report} />
    </section>
  )
}

function TeachingValidationReport({ plan, report }: { plan: TeachingPlanValue | null; report: TeachingPlanReport | null }) {
  if (!report) return null
  const coverage = teachingCoverageRows(plan, report)
  const orderedIssues = report.issues
    .map((issue, index) => ({ issue, index }))
    .sort((left, right) => issuePriority(left.issue) - issuePriority(right.issue) || left.index - right.index)
    .map(({ issue }) => issue)
  const shownIssues = orderedIssues.slice(0, 25)
  const remainingIssues = orderedIssues.slice(shownIssues.length)
  const highlightedIssue = orderedIssues.find((issue) => issue.severity === 'error' || issue.start_seconds !== undefined || issue.end_seconds !== undefined)
  return (
    <>
      {highlightedIssue && <p className="inline-note teaching-highlight"><strong>Priority finding:</strong> {highlightedIssue.message}{highlightedIssue.start_seconds !== undefined && highlightedIssue.end_seconds !== undefined ? ` (${highlightedIssue.start_seconds.toFixed(3)}–${highlightedIssue.end_seconds.toFixed(3)}s)` : ''}</p>}
      <details className="teaching-plan-section">
        <summary>Validation report <span>{report.issues.length} issue{report.issues.length === 1 ? '' : 's'} · {report.media_status === 'saved_revision' ? 'saved revision inspected' : 'draft not rendered'}</span></summary>
        <div className="coverage-list">
          <p className={report.can_save ? 'coverage-saveable' : 'coverage-blocked'}>{plan ? (report.can_save ? 'This plan may be saved. Missing coverage remains visible as warnings.' : 'Repair integrity errors before saving this teaching plan.') : 'This saved revision was inspected. Findings are structural diagnostics; no teaching plan is saved.'}</p>
          {coverage.map((row) => <article className="coverage-row" key={row.goal_id}><strong>{row.goalText || row.goal_id}</strong><span>Explanation scenes: {row.explanation_scene_ids.length ? row.explanation_scene_ids.join(', ') : 'none'}</span><span>Planned checks: {row.planned_check_ids.length ? row.planned_check_ids.join(', ') : 'none'}</span><span>Installed practice: {row.installed_practice_ids.length ? row.installed_practice_ids.join(', ') : 'none'}</span></article>)}
          <TeachingIssues issues={shownIssues} />
          {remainingIssues.length > 0 && <details className="teaching-more-issues"><summary>Show {remainingIssues.length} more findings</summary><TeachingIssues issues={remainingIssues} /></details>}
        </div>
      </details>
    </>
  )
}

function TeachingIssues({ issues }: { issues: TeachingPlanReport['issues'] }) {
  if (issues.length === 0) return null
  return <ul className="teaching-issues">{issues.map((issue, index) => <li className={issue.severity} key={`${issue.code}-${issue.path}-${index}`}><strong>{issue.severity}</strong> {issue.message}<small>{issue.path}{issue.start_seconds !== undefined && issue.end_seconds !== undefined ? ` · ${issue.start_seconds.toFixed(3)}–${issue.end_seconds.toFixed(3)}s` : ''}</small></li>)}</ul>
}

function issuePriority(issue: TeachingPlanReport['issues'][number]) {
  if (issue.severity === 'error') return 0
  if (issue.start_seconds !== undefined || issue.end_seconds !== undefined) return 1
  return 2
}

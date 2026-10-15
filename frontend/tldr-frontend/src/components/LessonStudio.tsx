import { useEffect, useMemo, useRef, useState } from 'react'
import {
  IconArrowRight,
  IconBook,
  IconClock,
  IconMovie,
  IconPlayerPlay,
  IconPlus,
  IconSparkles,
} from '../icons'
import { api } from '../lib/api'
import { newScene, rendererSpec, resolveLesson, storyboardErrors } from '../lib/lesson'
import { emptyTeachingPlan, teachingPlanForRevision, teachingPlanValidationKey, validationIsCurrent, validationRequest } from '../lib/teachingPlan'
import type { Course, Job, Lesson, LessonChapter, LessonRevision, LessonSpec, PracticeCheckpoint, Region, Source, TeachingPlan as TeachingPlanValue, TeachingPlanReport, VideoContext } from '../types'
import { MathText } from './MathText'
import { ConfirmDialog } from './ConfirmDialog'
import { SceneThumbnail, type SourceThumbnail } from './SceneThumbnail'
import { TeachingPlan } from './TeachingPlan'
import { sceneAtTime, sceneSeekTime, timelineSeconds } from '../lib/timeline'
import { crossedPractice } from '../lib/practice'
import { sceneCitations, type SceneReferences } from '../lib/sceneSources'

type Props = {
  active: boolean
  courseId: Course['id']
  lessons: Lesson[]
  demo: boolean
  onLessonsChange: (lessons: Lesson[]) => void
  onJobCreated: (job: Job) => void
  onVideoContext: (context: VideoContext) => void
  onSceneReferences: (context: SceneReferences | undefined) => void
  onNotice: (message: string) => void
  availableRefs: Array<{ id: string; label: string; regionId: Region['id'] }>
  sources: Source[]
  focusRevisionId?: string | number
  onRefresh: () => void
}

const blankSpec: LessonSpec = {
  title: 'New visual lesson',
  id: 'lesson-draft',
  target_minutes: 15,
  learning_objectives: ['Explain the central idea using source evidence.'],
  chapters: [{
    id: 'chapter-1',
    title: 'Opening idea',
    objective: 'Establish the question and visual model.',
    scenes: [newScene('scene-1')],
  }],
}

export function LessonStudio({ active, courseId, lessons, demo, onLessonsChange, onJobCreated, onVideoContext, onSceneReferences, onNotice, availableRefs, sources, focusRevisionId, onRefresh }: Props) {
  const [lessonId, setLessonId] = useState<Lesson['id'] | undefined>(lessons[0]?.id)
  const [revisionId, setRevisionId] = useState<LessonRevision['id'] | undefined>(lessons[0]?.revisions[lessons[0].revisions.length - 1]?.id)
  const [draft, setDraft] = useState<LessonSpec>(lessons[0]?.revisions[lessons[0].revisions.length - 1]?.spec ?? blankSpec)
  const [teachingPlan, setTeachingPlan] = useState<TeachingPlanValue | null>(teachingPlanForRevision(lessons[0]?.revisions[lessons[0].revisions.length - 1]))
  const [teachingReport, setTeachingReport] = useState<TeachingPlanReport | null>(null)
  const [validatingPlan, setValidatingPlan] = useState(false)
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState<'storyboard' | 'preview'>(lessons[0]?.revisions.length ? 'preview' : 'storyboard')
  const [creatingNew, setCreatingNew] = useState(lessons.length === 0)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const hydratedLessonKey = useRef<string | undefined>()
  const hydratedRevisionKey = useRef<string | undefined>()
  const focusedRevisionKey = useRef<string | undefined>()
  const validationRun = useRef(0)

  const lesson = resolveLesson(lessons, lessonId, creatingNew)
  const revision = lesson?.revisions.find((entry) => entry.id === revisionId) ?? lesson?.revisions[lesson.revisions.length - 1]
  const validationScope = teachingPlanValidationKey(courseId, revision?.id, rendererSpec(draft), teachingPlan)
  const currentValidationScope = useRef(validationScope)
  currentValidationScope.current = validationScope
  const sourceImages = useMemo(() => {
    const images: Record<string, SourceThumbnail> = {}
    const pages = sources.flatMap((source) => source.pages)
    for (const page of pages) {
      if (!page.image_url) continue
      const base = { url: page.image_url, width: page.width, height: page.height }
      images[`p${page.id}`] = { ...base, crop: { x: 0, y: 0, width: 1, height: 1 } }
      for (const region of page.regions) images[`r${region.id}`] = { ...base, crop: { x: region.x, y: region.y, width: region.width, height: region.height } }
    }
    for (const citation of revision?.citations ?? []) {
      const page = pages.find((candidate) => candidate.id === citation.page_id)
      if (!page?.image_url || !citation.source_asset) continue
      const key = citation.region_id ? `r${citation.region_id}` : `p${citation.page_id}`
      images[key] = { url: page.image_url, width: page.width, height: page.height, crop: citation.source_asset.crop }
    }
    return images
  }, [revision?.citations, sources])

  useEffect(() => {
    if (!creatingNew && !lessons.some((entry) => entry.id === lessonId)) setLessonId(lessons[0]?.id)
  }, [creatingNew, lessonId, lessons])

  useEffect(() => {
    const lessonKey = lesson ? `${courseId}:${lesson.id}` : undefined
    if (lesson && hydratedLessonKey.current !== lessonKey) {
      const nextRevision = lesson.revisions[lesson.revisions.length - 1]
      setRevisionId(nextRevision?.id)
      setDraft(nextRevision?.spec ?? { ...blankSpec, title: lesson.title })
      setTeachingPlan(teachingPlanForRevision(nextRevision))
      setTeachingReport(null)
      hydratedLessonKey.current = lessonKey
      hydratedRevisionKey.current = nextRevision ? `${courseId}:${lesson.id}:${nextRevision.id}` : undefined
    } else if (!lesson && hydratedLessonKey.current !== undefined) {
      setRevisionId(undefined)
      setDraft(blankSpec)
      setTeachingPlan(null)
      setTeachingReport(null)
      hydratedLessonKey.current = undefined
      hydratedRevisionKey.current = undefined
    }
  }, [courseId, lesson])

  useEffect(() => {
    const revisionKey = lesson && revision ? `${courseId}:${lesson.id}:${revision.id}` : undefined
    if (revision && hydratedRevisionKey.current !== revisionKey) {
      setDraft(revision.spec)
      setTeachingPlan(teachingPlanForRevision(revision))
      setTeachingReport(null)
      hydratedRevisionKey.current = revisionKey
    }
  }, [courseId, lesson, revision])

  useEffect(() => {
    validationRun.current += 1
    setValidatingPlan(false)
    setTeachingReport(null)
  }, [validationScope])

  useEffect(() => {
    const focusKey = focusRevisionId === undefined ? undefined : `${courseId}:${focusRevisionId}`
    if (focusRevisionId === undefined || focusedRevisionKey.current === focusKey) return
    const owner = lessons.find((entry) => entry.revisions.some((candidate) => candidate.id === focusRevisionId))
    if (owner) {
      focusedRevisionKey.current = focusKey
      setCreatingNew(false)
      setLessonId(owner.id)
      setRevisionId(focusRevisionId)
      setMode('preview')
    }
  }, [courseId, focusRevisionId, lessons])

  const selectableRefs = lesson && revision
    ? revision.citations.map((citation) => ({
      id: citation.region_id ? `r${citation.region_id}` : `p${citation.page_id}`,
      label: `${citation.source_title}, p. ${citation.page_number}${citation.region_id ? ' marked region' : ''}`,
    }))
    : availableRefs

  const updateChapter = (chapterIndex: number, patch: Partial<LessonChapter>) => {
    setDraft((current) => ({ ...current, chapters: current.chapters.map((chapter, index) => index === chapterIndex ? { ...chapter, ...patch } : chapter) }))
  }

  const updateScene = (chapterIndex: number, sceneIndex: number, patch: Partial<LessonChapter['scenes'][number]>) => {
    const chapter = draft.chapters[chapterIndex]
    updateChapter(chapterIndex, { scenes: chapter.scenes.map((scene, index) => index === sceneIndex ? { ...scene, ...patch } : scene) })
  }

  const validatePlan = async (): Promise<TeachingPlanReport | null> => {
    if (!revision) return null
    if (demo) {
      onNotice('Teaching-plan validation is available in the local app. The static demo makes no network requests.')
      return null
    }
    const spec = rendererSpec(draft)
    const requestScope = teachingPlanValidationKey(courseId, revision.id, spec, teachingPlan)
    const run = validationRun.current + 1
    validationRun.current = run
    const requestToken = { run, scope: requestScope }
    currentValidationScope.current = requestScope
    setValidatingPlan(true)
    try {
      const report = await api.validateTeachingPlan(courseId, validationRequest(revision, spec, teachingPlan))
      if (!validationIsCurrent(requestToken, { run: validationRun.current, scope: currentValidationScope.current })) return null
      setTeachingReport(report)
      return report
    } catch (error) {
      if (validationIsCurrent(requestToken, { run: validationRun.current, scope: currentValidationScope.current })) onNotice(error instanceof Error ? error.message : 'Teaching-plan coverage could not be validated.')
      return null
    } finally {
      if (validationIsCurrent(requestToken, { run: validationRun.current, scope: currentValidationScope.current })) setValidatingPlan(false)
    }
  }

  const saveRevision = async () => {
    setBusy(true)
    try {
      const errors = storyboardErrors(draft, { requireSourceRefs: Boolean(lesson) })
      if (errors.length) {
        onNotice(errors[0])
        return
      }
      if (demo) {
        onNotice('Storyboard edits stay in this browser preview. Demo mode does not start generation.')
        return
      }
      if (!lesson) {
        const selected = new Set(draft.chapters.flatMap((chapter) => chapter.scenes.flatMap((scene) => scene.source_refs)))
        const region_ids = availableRefs.filter((sourceRef) => selected.has(sourceRef.id)).map((sourceRef) => sourceRef.regionId)
        const response = await api.createLesson({ course: courseId, title: draft.title, prompt: storyboardPrompt(draft), target_minutes: draft.target_minutes, region_ids })
        onJobCreated(response.job)
        onNotice('Lesson outline queued. It will appear after validated generation completes.')
      } else {
        if (teachingPlan) {
          const report = await validatePlan()
          if (!report) return
          if (!report.can_save) {
            onNotice('Repair the teaching-plan integrity errors before saving this revision.')
            return
          }
        }
        const saved = await api.saveLessonRevision(lesson.id, { spec: rendererSpec(draft), citations: revision?.citations ?? [], ...(teachingPlan ? { teaching_plan: teachingPlan } : {}) })
        onLessonsChange(lessons.map((entry) => entry.id === lesson.id ? { ...entry, title: draft.title, revisions: [...entry.revisions, saved] } : entry))
        setRevisionId(saved.id)
        setTeachingPlan(teachingPlanForRevision(saved))
        onNotice('Storyboard saved as a new immutable revision. Review it before rendering.')
      }
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Lesson revision could not be queued.')
    } finally {
      setBusy(false)
    }
  }

  const render = async () => {
    if (!lesson || !revision) return
    setBusy(true)
    try {
      if (demo) {
        onNotice('The public demo shows a curated scene preview and does not render video.')
        return
      }
      const response = await api.renderLesson(lesson.id, revision.id)
      onJobCreated(response.job)
      onNotice('Video render queued. You can keep studying while it runs.')
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Video render could not be queued.')
    } finally {
      setBusy(false)
    }
  }

  const createFollowup = async (context: VideoContext) => {
    if (!lesson || !revision) return
    if (demo) {
      onNotice('Follow-up clip generation is available in the local app.')
      return
    }
    setBusy(true)
    try {
      const scene = revision.spec.chapters.flatMap((chapter) => chapter.scenes).find((entry) => entry.id === context.scene_id)
      const region_ids = (scene?.source_refs ?? []).filter((ref) => /^r\d+$/.test(ref)).map((ref) => Number(ref.slice(1)))
      const objectIds = context.object_ids ?? []
      const objectLabels = scene?.objects.filter((object) => objectIds.includes(object.id)).map((object) => object.label) ?? []
      const sourceContext = JSON.stringify({
        scene_title: scene?.title,
        scene_narration: scene?.narration,
        selected_objects: scene?.objects.filter((object) => objectIds.includes(object.id)),
      }).slice(0, 12000)
      const response = await api.createLesson({
        course: courseId,
        title: `${lesson.title}: ${scene?.title ?? 'focused follow-up'}`,
        prompt: `Create a focused follow-up video lesson from ${context.label}. Explain the next useful inference from this exact original scene context: ${sourceContext}. Focus on ${objectLabels.join(', ') || 'the scene as a whole'}. Keep the explanation concise and evidence-grounded. Return a separate storyboard for review before rendering so the original lesson stays available.`,
        target_minutes: 2,
        region_ids,
        purpose: 'followup',
        context: {
          revision_id: context.revision_id,
          scene_id: context.scene_id,
          time_seconds: context.time_seconds,
          object_ids: objectIds,
        },
      })
      onJobCreated(response.job)
      onNotice('Focused follow-up storyboard queued as a separate lesson. It will open for review when ready.')
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Follow-up clip could not be queued.')
    } finally { setBusy(false) }
  }

  const deleteLesson = async () => {
    if (!lesson) return
    if (demo) {
      onNotice('Demo lessons are curated and cannot be removed.')
      setConfirmDelete(false)
      return
    }
    setBusy(true)
    try {
      await api.deleteLesson(lesson.id)
      const remaining = lessons.filter((entry) => entry.id !== lesson.id)
      onLessonsChange(remaining)
      setLessonId(remaining[0]?.id)
      setCreatingNew(remaining.length === 0)
      setConfirmDelete(false)
      onNotice(`Removed ${lesson.title}.`)
      onRefresh()
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Lesson could not be removed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="lesson-studio" aria-label="Lesson studio">
      <header className="workspace-header">
        <div><span className="quiet-label">Lesson studio</span><h1>{lesson?.title ?? 'Build a visual lesson'}</h1></div>
        <div className="button-row">
          {lesson && lesson.revisions.length > 1 && <label className="revision-select"><span>Revision</span><select value={String(revision?.id ?? '')} onChange={(event) => setRevisionId(lesson.revisions.find((entry) => String(entry.id) === event.target.value)?.id)}>{lesson.revisions.map((entry) => <option value={String(entry.id)} key={entry.id}>Revision {entry.number}</option>)}</select></label>}
          <button className={mode === 'preview' ? 'segmented active' : 'segmented'} type="button" onClick={() => setMode('preview')} disabled={!revision}>Watch</button>
          <button className={mode === 'storyboard' ? 'segmented active' : 'segmented'} type="button" onClick={() => setMode('storyboard')}>Storyboard</button>
          {lesson && <button className="button compact danger-ghost" type="button" onClick={() => setConfirmDelete(true)}>Remove lesson</button>}
        </div>
      </header>

      <div className="lesson-picker" role="navigation" aria-label="Lessons">
        {lessons.map((entry) => (
          <button type="button" className={!creatingNew && entry.id === lesson?.id ? 'lesson-pick active' : 'lesson-pick'} onClick={() => { setCreatingNew(false); setLessonId(entry.id); setMode('preview') }} key={entry.id}>
            <IconBook size={18} aria-hidden="true" /><span>{entry.title}</span><small>{entry.revisions.length} revision{entry.revisions.length === 1 ? '' : 's'}</small>
          </button>
        ))}
        <button type="button" className={creatingNew ? 'lesson-pick new active' : 'lesson-pick new'} onClick={() => { setCreatingNew(true); setLessonId(undefined); setDraft(blankSpec); setTeachingPlan(null); setTeachingReport(null); setMode('storyboard') }}><IconPlus size={18} aria-hidden="true" /> New lesson</button>
      </div>

      <div className="lesson-mode-panel" hidden={mode !== 'storyboard'}>
        <div className="storyboard-layout">
          <aside className="lesson-brief">
            <label>Lesson title<input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
            <fieldset>
              <legend>Target length</legend>
              <div className="duration-options">
                {(draft.purpose === 'followup' ? [1, 2, 3] as const : [10, 15, 20] as const).map((minutes) => (
                  <button type="button" className={draft.target_minutes === minutes ? 'duration active' : 'duration'} aria-pressed={draft.target_minutes === minutes} onClick={() => setDraft({ ...draft, target_minutes: minutes })} key={minutes}><IconClock size={17} aria-hidden="true" /> {minutes} min</button>
                ))}
              </div>
            </fieldset>
            <label>Learning objectives<textarea value={(draft.learning_objectives ?? []).join('\n')} onChange={(event) => setDraft({ ...draft, learning_objectives: event.target.value.split('\n').filter(Boolean) })} rows={6} /><small>One objective per line.</small></label>
            <button className="button primary full" type="button" onClick={saveRevision} disabled={busy || !draft.title.trim()}><IconSparkles size={18} aria-hidden="true" /> {busy ? 'Saving' : lesson ? 'Save revision' : 'Generate first draft'}</button>
            <p className="inline-note">Existing revisions stay unchanged. Save this storyboard as a new revision, review it, then start rendering.</p>
          </aside>

          <div className="chapter-list">
            {lesson && revision ? <TeachingPlan revision={revision} spec={draft} plan={teachingPlan} report={teachingReport} validating={validatingPlan} demo={demo} onCreate={() => setTeachingPlan(emptyTeachingPlan())} onChange={setTeachingPlan} onValidate={() => void validatePlan()} /> : <p className="inline-note planning-after-storyboard">Generate the first storyboard before creating a teaching plan. Planning binds goals and evidence to stable scene IDs in a saved revision.</p>}
            {draft.chapters.map((chapter, chapterIndex) => (
              <article className="chapter" key={chapter.id}>
                <header><span>{chapterIndex + 1}</span><div><input aria-label={`Chapter ${chapterIndex + 1} title`} value={chapter.title} onChange={(event) => updateChapter(chapterIndex, { title: event.target.value })} /><input className="objective-input" aria-label={`Chapter ${chapterIndex + 1} objective`} value={chapter.objective ?? ''} onChange={(event) => updateChapter(chapterIndex, { objective: event.target.value })} placeholder="Chapter objective" /></div></header>
                <div className="scene-strip">
                  {chapter.scenes.map((scene, sceneIndex) => (
                    <section className="scene-card" key={scene.id}>
                      <div className="scene-order">Scene {chapterIndex + 1}.{sceneIndex + 1}</div>
                      <label>Title<input value={scene.title} onChange={(event) => updateChapter(chapterIndex, { scenes: chapter.scenes.map((entry, index) => index === sceneIndex ? { ...entry, title: event.target.value } : entry) })} /></label>
                      <label>Objective<input value={scene.objective ?? ''} onChange={(event) => updateChapter(chapterIndex, { scenes: chapter.scenes.map((entry, index) => index === sceneIndex ? { ...entry, objective: event.target.value } : entry) })} /></label>
                      <label>Narration<textarea rows={4} value={scene.narration} onChange={(event) => updateChapter(chapterIndex, { scenes: chapter.scenes.map((entry, index) => index === sceneIndex ? { ...entry, narration: event.target.value } : entry) })} /></label>
                      <fieldset className="source-ref-picker"><legend>Source evidence</legend>{selectableRefs.length ? selectableRefs.map((sourceRef) => <button type="button" aria-pressed={scene.source_refs.includes(sourceRef.id)} className={scene.source_refs.includes(sourceRef.id) ? 'source-ref active' : 'source-ref'} onClick={() => updateChapter(chapterIndex, { scenes: chapter.scenes.map((entry, index) => index === sceneIndex ? { ...entry, source_refs: entry.source_refs.includes(sourceRef.id) ? entry.source_refs.filter((id) => id !== sourceRef.id) : [...entry.source_refs, sourceRef.id] } : entry) })} key={sourceRef.id}>{sourceRef.label}</button>) : <p>{lesson ? 'This revision has no reusable citations.' : 'Optional: mark a page region in Sources to focus generation on exact visual evidence.'}</p>}</fieldset>
                      <SceneThumbnail scene={scene} sourceImages={sourceImages} />
                      {scene.objects.filter((object) => object.kind === 'equation').map((object) => <details className="math-edit-preview" key={object.id}><summary>Edit equation math</summary><label>Equation LaTeX<textarea rows={3} value={object.latex ?? ''} placeholder={String.raw`\frac{1}{2}x^2`} onChange={(event) => { const latex = event.target.value; updateScene(chapterIndex, sceneIndex, { objects: scene.objects.map((entry) => { if (entry.id !== object.id) return entry; const next = { ...entry }; if (latex.trim()) next.latex = latex; else delete next.latex; return next }) }) }} /></label><small>Math notation only, without delimiters. Leave empty to keep the existing plain equation. Notation does not verify the calculation.</small>{object.latex && <MathText text={`\\[${object.latex}\\]`} />}</details>)}
                      <fieldset className="scene-steps"><legend>Planned transformations</legend>{(scene.steps ?? []).map((step, stepIndex) => <div className="scene-step" key={`${scene.id}-step-${stepIndex}`}><label>Step {stepIndex + 1} caption<input value={step.caption} onChange={(event) => updateScene(chapterIndex, sceneIndex, { steps: (scene.steps ?? []).map((entry, index) => index === stepIndex ? { ...entry, caption: event.target.value } : entry) })} /></label><div className="step-objects" aria-label={`Step ${stepIndex + 1} visible objects`}>{scene.objects.map((object) => { const selected = step.object_ids.includes(object.id); return <button type="button" aria-pressed={selected} className={selected ? 'source-ref active' : 'source-ref'} onClick={() => updateScene(chapterIndex, sceneIndex, { steps: (scene.steps ?? []).map((entry, index) => index === stepIndex ? { ...entry, object_ids: selected ? (entry.object_ids.length > 1 ? entry.object_ids.filter((id) => id !== object.id) : entry.object_ids) : [...entry.object_ids, object.id] } : entry) })} key={object.id}>{object.label}</button> })}</div></div>)}</fieldset>
                      <div className="scene-meta"><span>{scene.objects.length} visual object{scene.objects.length === 1 ? '' : 's'}</span><span>{scene.source_refs.length} source ref{scene.source_refs.length === 1 ? '' : 's'}</span></div>
                    </section>
                  ))}
                  <button className="add-scene" type="button" onClick={() => updateChapter(chapterIndex, { scenes: [...chapter.scenes, newScene()] })}><IconPlus size={18} aria-hidden="true" /> Add scene</button>
                </div>
              </article>
            ))}
            <button className="button" type="button" onClick={() => setDraft({ ...draft, chapters: [...draft.chapters, { id: `chapter-${Date.now()}`, title: 'New chapter', objective: 'Explain the next idea.', scenes: [newScene()] }] })}><IconPlus size={18} aria-hidden="true" /> Add chapter</button>
          </div>
        </div>
      </div>
      {revision && <div className="lesson-mode-panel" hidden={mode !== 'preview'}><LessonPreview active={active && mode === 'preview'} revision={revision} sources={sources} onSceneReferences={onSceneReferences} sourceImages={sourceImages} demo={demo} onRender={render} onFollowup={createFollowup} busy={busy} onContext={onVideoContext} /></div>}
      {confirmDelete && lesson && <ConfirmDialog title={`Remove ${lesson.title}?`} message="This removes every revision and rendered artifact for the lesson. This cannot be undone." confirmLabel="Remove lesson" busy={busy} onCancel={() => setConfirmDelete(false)} onConfirm={() => void deleteLesson()} />}
    </section>
  )
}

function LessonPreview({ active, revision, sources, onSceneReferences, sourceImages, demo, onRender, onFollowup, busy, onContext }: { active: boolean; revision: LessonRevision; sources: Source[]; onSceneReferences: (context: SceneReferences | undefined) => void; sourceImages: Record<string, SourceThumbnail>; demo: boolean; onRender: () => void; onFollowup: (context: VideoContext) => void; busy: boolean; onContext: (context: VideoContext) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const scenes = useMemo(() => revision.spec.chapters.flatMap((chapter) => chapter.scenes.map((scene) => {
    const rendered = revision.manifest?.scenes?.find((entry) => entry.scene_id === scene.id)
    return {
      ...scene,
      objects: rendered?.objects ?? scene.objects,
      start_seconds: rendered?.start_seconds ?? scene.start_seconds,
      end_seconds: rendered?.end_seconds ?? scene.end_seconds,
      chapterId: chapter.id,
      chapterTitle: chapter.title,
    }
  })), [revision.manifest, revision.spec])
  const duration = revision.manifest?.duration_seconds ?? Math.max(1, ...scenes.map((scene) => scene.end_seconds ?? scene.start_seconds ?? 0))
  const [time, setTime] = useState(0)
  const [sceneId, setSceneId] = useState(scenes[0]?.id)
  const [objectIds, setObjectIds] = useState<string[]>([])
  const [pauseAtPractice, setPauseAtPractice] = useState(true)
  const [practice, setPractice] = useState<PracticeCheckpoint>()
  const [answerVisible, setAnswerVisible] = useState(false)
  const [showCaptions, setShowCaptions] = useState(true)
  const previousVideoTime = useRef(0)
  const seenPractice = useRef(new Set<string>())
  const practicePoints = revision.manifest?.practice ?? []
  const cues = revision.manifest?.cues ?? []
  const activeCue = cues.find((cue) => time >= cue.start_seconds && time < cue.end_seconds)
  const scene = (revision.video_url ? sceneAtTime(scenes, time, duration) : undefined) ?? scenes.find((entry) => entry.id === sceneId) ?? scenes[0]
  useEffect(() => {
    onSceneReferences(active && scene ? { revisionId: revision.id, sceneId: scene.id, title: scene.title, citations: sceneCitations(revision, scene, sources) } : undefined)
    return () => onSceneReferences(undefined)
  }, [active, scene, revision, sources, onSceneReferences])
  const firstSceneId = scenes[0]?.id
  const chapters = revision.spec.chapters.map((chapter) => ({
    ...chapter,
    firstScene: scenes.find((candidate) => candidate.chapterId === chapter.id),
  }))

  useEffect(() => {
    setTime(0)
    setSceneId(firstSceneId)
    setObjectIds([])
    setPractice(undefined)
    setAnswerVisible(false)
    previousVideoTime.current = 0
    seenPractice.current = new Set()
    videoRef.current?.load()
  }, [firstSceneId, revision.id])

  useEffect(() => {
    if (!active) videoRef.current?.pause()
  }, [active])

  useEffect(() => {
    if (!revision.video_url) return
    const current = sceneAtTime(scenes, time, duration)
    if (current && current.id !== sceneId) {
      setSceneId(current.id)
      setObjectIds([])
    }
  }, [duration, revision.video_url, sceneId, scenes, time])

  const seek = (seconds: number) => {
    previousVideoTime.current = seconds
    setPractice(undefined)
    setAnswerVisible(false)
    setTime(seconds)
    if (videoRef.current) videoRef.current.currentTime = seconds
  }

  const playVideo = () => {
    const attempt = videoRef.current?.play()
    if (attempt) void attempt.catch(() => undefined)
  }

  const openPractice = (point: PracticeCheckpoint) => {
    seenPractice.current.add(point.id)
    videoRef.current?.pause()
    seek(point.time_seconds)
    setPractice(point)
  }

  const updatePlaybackTime = (video: HTMLVideoElement) => {
    const current = video.currentTime
    const crossed = pauseAtPractice && !video.paused && !video.seeking
      ? crossedPractice(practicePoints, previousVideoTime.current, current, seenPractice.current)
      : undefined
    previousVideoTime.current = current
    if (crossed) openPractice(crossed)
    else setTime(current)
  }

  const captureContext = (): VideoContext | undefined => {
    const actualTime = timelineSeconds(videoRef.current?.currentTime ?? time)
    videoRef.current?.pause()
    const actualScene = (revision.video_url ? sceneAtTime(scenes, actualTime, duration) : undefined) ?? scene
    if (!actualScene) return undefined
    setTime(actualTime)
    return { revision_id: revision.id, scene_id: actualScene.id, time_seconds: actualTime, object_ids: actualScene.id === scene?.id ? objectIds : [], label: `${actualScene.title} at ${formatTime(actualTime)}` }
  }

  return (
    <div className="preview-layout">
      <div className="video-stage">
        <div className="video-frame">
          {revision.video_url ? (
            <video key={String(revision.id)} ref={videoRef} controls poster={revision.poster_url} onTimeUpdate={(event) => updatePlaybackTime(event.currentTarget)} onSeeking={(event) => { previousVideoTime.current = event.currentTarget.currentTime }} onPlay={() => setPractice(undefined)}>
              <source src={revision.video_url} />
              {revision.captions_url && <track default={cues.length === 0} kind="captions" src={revision.captions_url} srcLang="en" label="English" />}
            </video>
          ) : (
            <ScenePreview scene={scene} sourceImages={sourceImages} />
          )}
        </div>
        <div className="cinema-chapters"><h3>Chapters</h3><div className="chapter-track">{chapters.map((chapter, index) => <button type="button" aria-label={`Play chapter ${index + 1}: ${chapter.title}`} className={chapter.id === scene?.chapterId ? 'chapter-cue active' : 'chapter-cue'} onClick={() => { if (chapter.firstScene) { setSceneId(chapter.firstScene.id); seek(sceneSeekTime(chapter.firstScene, duration)); setObjectIds([]) } }} key={chapter.id}><SceneThumbnail scene={chapter.firstScene ?? chapter.scenes[0]} sourceImages={sourceImages} /><span><strong>{index + 1}. {chapter.title}</strong><small>{revision.video_url ? formatTime(chapter.firstScene?.start_seconds ?? chapter.start_seconds ?? 0) : 'Storyboard'}</small></span></button>)}</div></div>
        {cues.length > 0 && <><label className="caption-toggle"><input type="checkbox" checked={showCaptions} onChange={(event) => setShowCaptions(event.target.checked)} /> Captions</label>{showCaptions && <div className="lesson-captions" role="region" aria-label="Captions" aria-live="off"><MathText text={activeCue?.text ?? practice?.question ?? '\u00a0'} /></div>}</>}
        <div className="duration-note"><IconClock size={16} aria-hidden="true" /><span>{revision.video_url ? `Lesson ${formatTime(duration)}` : 'Storyboard preview. Video has not been rendered.'}</span></div>
        {practicePoints.length > 0 && <details className="practice-jumps"><summary>Practice checkpoints <span>{practicePoints.length}</span></summary><div className="practice-controls"><label><input type="checkbox" checked={pauseAtPractice} onChange={(event) => setPauseAtPractice(event.target.checked)} /> Pause at practice questions</label><div className="button-row">{practicePoints.map((point, index) => <button type="button" className="button compact" key={point.id} onClick={() => openPractice(point)} title={point.question}>Practice {index + 1} · {formatTime(point.time_seconds)}</button>)}</div></div></details>}
        {practice && <section className="practice-card" aria-label="Practice question"><span className="quiet-label">Pause and think</span><h3><MathText text={practice.question} /></h3>{answerVisible && <p><MathText text={practice.answer} /></p>}<div className="button-row"><button className="button" type="button" onClick={() => setAnswerVisible((value) => !value)}>{answerVisible ? 'Hide explanation' : 'Reveal explanation'}</button><button className="button primary" type="button" onClick={() => { setPractice(undefined); playVideo() }}>Continue lesson <IconPlayerPlay size={16} aria-hidden="true" /></button></div><small>Revealing an explanation does not mark this concept as learned.</small></section>}
        {revision.manifest?.warnings?.map((warning) => <p className="inline-note" key={warning}>{warning}</p>)}
        {!revision.video_url && (
          <div className="render-callout"><div><strong>{demo ? 'Curated scene preview' : 'Storyboard is ready to render'}</strong><p>{demo ? 'This browser demo uses interactive scene art and no generated media.' : 'Rendering creates the video, captions, transcript, and timestamp manifest.'}</p></div><button className="button primary" type="button" onClick={onRender} disabled={busy}><IconMovie size={18} aria-hidden="true" /> {busy ? 'Queuing' : demo ? 'Demo render info' : 'Render video'}</button></div>
        )}
      </div>

      <aside className="transcript-panel">
        <header><div><span className="quiet-label">Transcript and objects</span><h2>{scene?.title ?? 'Scene'}</h2></div><span className="status-tag">{formatTime(scene?.start_seconds ?? 0)}</span></header>
        {scene && <p className="scene-narration"><MathText text={scene.narration} /></p>}
        {scene?.objects.length ? (
          <fieldset className="object-picker"><legend>Select visual context</legend>{scene.objects.map((object) => <button type="button" aria-pressed={objectIds.includes(object.id)} className={objectIds.includes(object.id) ? 'object-chip active' : 'object-chip'} onClick={() => setObjectIds((items) => items.includes(object.id) ? items.filter((id) => id !== object.id) : [...items, object.id])} key={object.id}>{object.label}</button>)}</fieldset>
        ) : null}
        {scene && <div className="preview-actions"><button className="button primary full" type="button" onClick={() => { const context = captureContext(); if (context) onContext(context) }}>Ask about this moment <IconArrowRight size={18} aria-hidden="true" /></button><button className="button full" type="button" disabled={busy} onClick={() => { const context = captureContext(); if (context) onFollowup(context) }}><IconMovie size={18} aria-hidden="true" /> Create focused follow-up lesson</button></div>}
        <details className="full-transcript"><summary>Full transcript <span>{scenes.length} scenes</span></summary><div>{scenes.map((entry) => <button type="button" className={entry.id === scene?.id ? 'transcript-scene active' : 'transcript-scene'} onClick={() => { setSceneId(entry.id); seek(sceneSeekTime(entry, duration)); setObjectIds([]) }} key={entry.id}><span>{formatTime(entry.start_seconds ?? 0)}</span><span><strong>{entry.title}</strong><small>{entry.narration}</small></span></button>)}</div></details>
      </aside>
    </div>
  )
}

function ScenePreview({ scene, sourceImages }: { scene?: LessonChapter['scenes'][number] & { chapterTitle: string }; sourceImages: Record<string, SourceThumbnail> }) {
  return (
    <div className="scene-preview" aria-label={scene ? `Scene preview: ${scene.title}` : 'Scene preview unavailable'}>
      {scene ? <SceneThumbnail scene={scene} sourceImages={sourceImages} /> : <p>No scene preview is available.</p>}
    </div>
  )
}

function storyboardPrompt(spec: LessonSpec) {
  const outline = spec.chapters.map((chapter) => `${chapter.title}: ${chapter.objective ?? ''}\n${chapter.scenes.map((scene) => `- ${scene.title}: ${scene.objective ?? ''} ${scene.narration}`.trim()).join('\n')}`).join('\n\n')
  return `Create a ${spec.target_minutes}-minute visual lesson titled "${spec.title}".\n\nLearning objectives:\n${(spec.learning_objectives ?? []).map((objective) => `- ${objective}`).join('\n')}\n\nStoryboard constraints:\n${outline}`
}

function formatTime(seconds: number) {
  const rounded = Math.max(0, Math.floor(seconds))
  return `${Math.floor(rounded / 60)}:${String(rounded % 60).padStart(2, '0')}`
}

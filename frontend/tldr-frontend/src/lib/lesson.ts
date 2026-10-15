import type { Lesson, LessonScene, LessonSpec } from '../types'

export function resolveLesson(lessons: Lesson[], selectedId: Lesson['id'] | undefined, creatingNew: boolean) {
  if (creatingNew) return undefined
  return lessons.find((lesson) => lesson.id === selectedId) ?? lessons[0]
}

export function newScene(id = `scene-${Date.now()}`): LessonScene {
  return {
    id,
    title: 'New scene',
    objective: 'Explain one visible change.',
    narration: 'Explain the main idea and connect it to the selected source evidence.',
    source_refs: [],
    objects: [{ id: `${id}-text`, kind: 'text', label: 'Main idea', text: 'Main idea' }],
    steps: [{ object_ids: [`${id}-text`], caption: 'Introduce the main idea.' }],
  }
}

export function rendererSpec(spec: LessonSpec): LessonSpec {
  return {
    id: spec.id ?? 'lesson-draft',
    title: spec.title.trim(),
    target_minutes: spec.target_minutes,
    ...(spec.purpose ? { purpose: spec.purpose } : {}),
    learning_objectives: spec.learning_objectives?.map((objective) => objective.trim()).filter(Boolean),
    chapters: spec.chapters.map((chapter) => ({
      id: chapter.id,
      title: chapter.title.trim(),
      objective: chapter.objective?.trim() || undefined,
      scenes: chapter.scenes.map((scene) => ({
        id: scene.id,
        title: scene.title.trim(),
        objective: scene.objective?.trim() || undefined,
        narration: scene.narration.trim(),
        source_refs: scene.source_refs,
        objects: scene.objects,
        steps: (scene.steps ?? []).map((step) => ({
          object_ids: step.object_ids,
          caption: step.caption,
          ...(step.narration_anchor && scene.narration.includes(step.narration_anchor)
            ? { narration_anchor: step.narration_anchor }
            : {}),
        })),
      })),
    })),
  }
}

export function storyboardErrors(spec: LessonSpec, options: { requireSourceRefs?: boolean } = {}) {
  const issues: string[] = []
  if (!spec.title.trim()) issues.push('Add a lesson title.')
  if (spec.chapters.length === 0) issues.push('Add at least one chapter.')
  spec.chapters.forEach((chapter, chapterIndex) => {
    if (!chapter.title.trim()) issues.push(`Chapter ${chapterIndex + 1} needs a title.`)
    if (chapter.scenes.length === 0) issues.push(`${chapter.title || `Chapter ${chapterIndex + 1}`} needs at least one scene.`)
    chapter.scenes.forEach((scene, sceneIndex) => {
      const label = `Scene ${chapterIndex + 1}.${sceneIndex + 1}`
      if (!scene.title.trim()) issues.push(`${label} needs a title.`)
      if (scene.narration.trim().length < 20) issues.push(`${label} narration needs at least 20 characters.`)
      if (scene.objects.length === 0) issues.push(`${label} needs at least one visual object.`)
      scene.objects.forEach((object) => {
        if (object.kind === 'source_image' && (!object.source_ref || !scene.source_refs.includes(object.source_ref))) issues.push(`${label} source image must use one of the scene citations.`)
      })
      if (!scene.steps?.length) issues.push(`${label} needs at least one visual step.`)
      scene.steps?.forEach((step, stepIndex) => {
        if (!step.caption.trim()) issues.push(`${label}, step ${stepIndex + 1} needs a caption.`)
        if (!step.object_ids.length || step.object_ids.some((id) => !scene.objects.some((object) => object.id === id))) issues.push(`${label}, step ${stepIndex + 1} must use scene objects.`)
      })
      if (options.requireSourceRefs && scene.source_refs.length === 0) issues.push(`${label} needs at least one source reference.`)
    })
  })
  return issues
}

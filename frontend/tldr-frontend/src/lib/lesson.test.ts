import { describe, expect, it } from 'vitest'
import type { Lesson, LessonSpec } from '../types'
import { newScene, rendererSpec, resolveLesson, storyboardErrors } from './lesson'

const lesson = (id: string): Lesson => ({ id, course: 'course', title: id, revisions: [] })

describe('lesson editor state boundaries', () => {
  it('does not fall back to an existing lesson while creating a new one', () => {
    expect(resolveLesson([lesson('first')], undefined, true)).toBeUndefined()
    expect(resolveLesson([lesson('first')], undefined, false)?.id).toBe('first')
  })

  it('serializes only the renderer lesson contract with stable IDs', () => {
    const scene = {
      ...newScene('scene-alpha'),
      source_refs: ['r2'],
      steps: [{ object_ids: ['scene-alpha-text'], caption: 'Introduce the main idea.', narration_anchor: 'stale phrase' }],
    }
    const draft: LessonSpec = {
      title: '  Visual read  ',
      target_minutes: 15,
      learning_objectives: ['  Explain the read path.  '],
      chapters: [{ id: 'chapter-alpha', title: '  Read cycle  ', objective: '  Trace the bus. ', scenes: [scene] }],
    }
    expect(rendererSpec(draft)).toEqual({
      id: 'lesson-draft',
      title: 'Visual read',
      target_minutes: 15,
      learning_objectives: ['Explain the read path.'],
      chapters: [{
        id: 'chapter-alpha',
        title: 'Read cycle',
        objective: 'Trace the bus.',
        scenes: [{ ...scene, objective: 'Explain one visible change.', narration: scene.narration, steps: [{ object_ids: ['scene-alpha-text'], caption: 'Introduce the main idea.' }] }],
      }],
    })
    expect(storyboardErrors(draft, { requireSourceRefs: true })).toEqual([])
    expect(storyboardErrors({ ...draft, chapters: [{ ...draft.chapters[0], scenes: [newScene('uncited-draft')] }] })).toEqual([])
    expect(rendererSpec({ ...draft, purpose: 'followup', target_minutes: 2 })).toMatchObject({ purpose: 'followup', target_minutes: 2 })
  })
})

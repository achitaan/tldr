import type { Citation, Id, LessonRevision, LessonScene, Source } from '../types'

export type SceneReferences = { revisionId: Id; sceneId: string; title: string; citations: Citation[] }

// Only show references already recorded in this revision and still resolvable
// inside the selected course. A scene label alone is not evidence.
export function sceneCitations(revision: Pick<LessonRevision, 'citations'>, scene: Pick<LessonScene, 'source_refs'>, sources: Source[]): Citation[] {
  const references = new Set(scene.source_refs)
  const seen = new Set<string>()
  return revision.citations.filter((citation) => {
    const key = citation.region_id !== undefined ? `r${citation.region_id}` : `p${citation.page_id}`
    if (!references.has(key) || seen.has(key)) return false
    const source = sources.find((entry) => entry.id === citation.source_id)
    const page = source?.pages.find((entry) => entry.id === citation.page_id)
    if (!page || (citation.region_id !== undefined && !page.regions.some((region) => region.id === citation.region_id))) return false
    seen.add(key)
    return true
  })
}

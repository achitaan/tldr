export type Id = number | string

export type Course = {
  id: Id
  name: string
  description?: string
  created_at?: string
}

export type Region = {
  id: Id
  page: Id
  label: string
  x: number
  y: number
  width: number
  height: number
  text?: string
  confirmed?: boolean
}

export type SourcePage = {
  id: Id
  source: Id
  number: number
  text: string
  original_text?: string
  corrected?: boolean
  image_url?: string
  width: number
  height: number
  regions: Region[]
  demo_kind?: 'bus' | 'math' | 'finance' | 'biology'
}

export type Source = {
  id: Id
  course: Id
  title: string
  kind: string
  status: 'queued' | 'ready' | 'error'
  error?: string
  original_url?: string
  source_url?: string
  fetched_url?: string
  fetched_at?: string
  digest?: string
  extraction_notes?: string
  created_at?: string
  pages: SourcePage[]
}

export type Citation = {
  page_id: Id
  source_id: Id
  source_title: string
  page_number: number
  quote: string
  region_id?: Id
  visual?: boolean
  source_asset?: {
    page_id: Id
    source_id: Id
    region_id?: Id
    image_sha256: string
    pixel_width: number
    pixel_height: number
    crop: { x: number; y: number; width: number; height: number }
  }
}

export type Message = {
  id: Id
  conversation: Id
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  context?: ChatContext
  status: 'pending' | 'complete' | 'error'
  created_at?: string
  curated?: boolean
}

export type Conversation = {
  id: Id
  course: Id
  title: string
}

export type ChatContext = {
  revision_id?: Id
  scene_id?: string
  time_seconds?: number
  object_ids?: string[]
}

export type SceneObject = {
  id: string
  kind: string
  label: string
  bounds?: { x: number; y: number; width: number; height: number }
  text?: string
  latex?: string
  points?: number[][]
  shape?: 'circle' | 'rectangle' | 'triangle'
  nodes?: string[]
  signals?: Array<{ name: string; values: Array<0 | 1> }>
  calculation?: { kind: string; inputs: Record<string, string | number> }
  source_ref?: string
  overlays?: Array<{ x: number; y: number; width: number; height: number }>
  provenance?: 'original_source' | 'verified_tool' | 'conceptual'
  asset_sha256?: string
  crop?: { x: number; y: number; width: number; height: number }
}

export type LessonScene = {
  id: string
  scene_id?: string
  title: string
  objective?: string
  narration: string
  source_refs: string[]
  objects: SceneObject[]
  steps?: { object_ids: string[]; caption: string; narration_anchor?: string }[]
  start_seconds?: number
  end_seconds?: number
}

export type LessonChapter = {
  id: string
  title: string
  objective?: string
  start_seconds?: number
  end_seconds?: number
  scenes: LessonScene[]
}

export type LessonSpec = {
  id?: string
  title: string
  target_minutes: 1 | 2 | 3 | 10 | 15 | 20
  purpose?: 'lesson' | 'followup'
  learning_objectives?: string[]
  chapters: LessonChapter[]
}

export type TeachingGoal = {
  id: string
  text: string
  requires: string[]
}

export type TeachingPrerequisite = {
  id: string
  text: string
}

export type TeachingEvidenceBinding = {
  source_ref: string
  fingerprint: string
}

export type TeachingVisualRequest = {
  object_id: string
  kind: string
  purpose: string
}

export type TeachingCheck = {
  id: string
  goal_ids: string[]
  question: string
  expected_reasoning: string
}

export type TeachingScenePlan = {
  scene_id: string
  goal_ids: string[]
  evidence: TeachingEvidenceBinding[]
  visual_requests: TeachingVisualRequest[]
  checks: TeachingCheck[]
}

export type TeachingPlan = {
  version: 1
  goals: TeachingGoal[]
  assumed_prerequisites: TeachingPrerequisite[]
  scenes: TeachingScenePlan[]
}

export type TeachingPlanIssue = {
  code: string
  severity: 'error' | 'warning'
  path: string
  message: string
  scene_id?: string
  goal_id?: string
  start_seconds?: number
  end_seconds?: number
}

export type TeachingGoalCoverage = {
  goal_id: string
  explanation_scene_ids: string[]
  planned_check_ids: string[]
  installed_practice_ids: string[]
}

export type TeachingPlanReport = {
  plan_status: 'missing' | 'incomplete' | 'complete'
  can_save: boolean
  issues: TeachingPlanIssue[]
  coverage: TeachingGoalCoverage[]
  evidence_bindings: TeachingEvidenceBinding[]
  media_status: 'saved_revision' | 'draft_not_rendered'
}

export type LessonRevision = {
  id: Id
  lesson: Id
  number: number
  spec: LessonSpec
  teaching_plan?: TeachingPlan | null
  citations: Citation[]
  video_url?: string
  captions_url?: string
  transcript_url?: string
  poster_url?: string
  manifest?: {
    duration_seconds: number
    warnings?: string[]
    scope?: string
    status?: string
    caption_alignment?: string
    narration_engine?: string
    voice?: string
    model_hashes?: Record<string, string>
    scenes?: Array<{
      scene_id: string
      chapter_id: string
      title?: string
      start_seconds: number
      end_seconds: number
      source_refs?: string[]
      objects?: SceneObject[]
    }>
    chapters?: Array<{ id: string; title: string; start_seconds: number; end_seconds: number }>
    cues?: Array<{ start_seconds: number; end_seconds: number; text: string; scene_id?: string }>
    practice?: PracticeCheckpoint[]
    provenance?: {
      categories: Record<'original_source' | 'verified_tool' | 'conceptual', string>
      counts: Record<'original_source' | 'verified_tool' | 'conceptual', number>
    }
  }
  created_at?: string
}

export type Lesson = {
  id: Id
  course: Id
  title: string
  created_at?: string
  revisions: LessonRevision[]
  jobs?: Job[]
}

export type PracticeCheckpoint = {
  id: string
  scene_id: string
  time_seconds: number
  question: string
  answer: string
}

export type Job = {
  id: Id
  course: Id
  kind: 'ingest' | 'chat' | 'lesson' | 'render'
  status: 'queued' | 'running' | 'complete' | 'failed' | 'cancelled' | 'paused'
  progress: number
  error?: string
  result?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export type StudyKind = 'flashcard' | 'quiz' | 'checklist' | 'bookmark' | 'confusion'

export type StudyItem = {
  id: Id
  course: Id
  kind: StudyKind
  title: string
  body?: string
  data: Record<string, unknown>
  page?: Id
  lesson?: Id
  completed: boolean
}

export type ServiceStatus = {
  provider: string
  model: string
  generation_enabled: boolean
  configuration_issues: string[]
  quota_paused: boolean
  ocr_available: boolean
  embedding_enabled: boolean
  embedding_model?: string
  worker: string | { status?: string }
}

export type CourseBundle = {
  sources: Source[]
  conversations: Conversation[]
  lessons: Lesson[]
  jobs: Job[]
  studyItems: StudyItem[]
}

export type CitationTarget = {
  sourceId: Id
  pageId: Id
  regionId?: Id
}

export type VideoContext = ChatContext & {
  label: string
}

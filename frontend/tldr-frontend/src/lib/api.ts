import type {
  Conversation,
  Course,
  CourseBundle,
  Job,
  Lesson,
  Message,
  Region,
  ServiceStatus,
  Source,
  SourcePage,
  StudyItem,
  TeachingPlan,
  TeachingPlanReport,
} from '../types'

const API_ROOT = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? '/api'

type RequestOptions = Omit<RequestInit, 'body'> & { body?: unknown }

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const isFormData = options.body instanceof FormData
  if (options.body !== undefined && !isFormData) headers.set('Content-Type', 'application/json')
  let requestBody: BodyInit | undefined
  if (options.body instanceof FormData) requestBody = options.body
  else if (options.body !== undefined) requestBody = JSON.stringify(options.body)

  let response: Response
  try {
    response = await fetch(`${API_ROOT}${path}`, {
      ...options,
      headers,
      body: requestBody,
    })
  } catch {
    throw new ApiError(0, 'The local study service could not be reached.')
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as unknown
    const directDetail = payload && typeof payload === 'object' && 'detail' in payload ? (payload as { detail?: unknown }).detail : undefined
    const detail = typeof directDetail === 'string'
      ? directDetail
      : payload
        ? formatApiError(payload)
        : `Request failed with status ${response.status}.`
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function formatApiError(payload: unknown): string {
  const messages = flattenApiError(payload)
  return messages.length ? messages.join(' ') : 'The request could not be completed.'
}

function flattenApiError(value: unknown, prefix = ''): string[] {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return [`${prefix ? `${prefix}: ` : ''}${String(value)}`]
  }
  if (Array.isArray(value)) return value.flatMap((entry) => flattenApiError(entry, prefix))
  if (!value || typeof value !== 'object') return []
  const record = value as Record<string, unknown>
  if (typeof record.message === 'string') {
    const path = typeof record.path === 'string' ? record.path : prefix
    return [`${path ? `${path}: ` : ''}${record.message}`]
  }
  return Object.entries(record).flatMap(([key, entry]) => flattenApiError(entry, prefix ? `${prefix}.${key}` : key))
}

export const api = {
  status: (signal?: AbortSignal) => request<ServiceStatus>('/status/', { signal }),
  resumeService: () => request<ServiceStatus>('/status/resume/', { method: 'POST' }),
  courses: (signal?: AbortSignal) => request<Course[]>('/courses/', { signal }),
  createCourse: (body: Pick<Course, 'name' | 'description'>) => request<Course>('/courses/', { method: 'POST', body }),
  deleteCourse: (course: Course['id']) => request<void>(`/courses/${course}/`, { method: 'DELETE' }),
  exportCourseUrl: (course: Course['id']) => `${API_ROOT}/courses/${course}/export/`,
  sources: (course: Course['id'], signal?: AbortSignal) => request<Source[]>(`/sources/?course=${course}`, { signal }),
  createTextSource: (course: Course['id'], title: string, text: string) => request<Source>('/sources/', { method: 'POST', body: { course, title, text } }),
  createWebSource: (course: Course['id'], url: string, title: string) => request<Source>('/sources/', { method: 'POST', body: { course, url, ...(title.trim() ? { title } : {}) } }),
  uploadSource: (course: Course['id'], file: File) => {
    const body = new FormData()
    body.append('course', String(course))
    body.append('file', file)
    body.append('title', file.name)
    return request<Source>('/sources/', { method: 'POST', body })
  },
  deleteSource: (source: Source['id']) => request<void>(`/sources/${source}/`, { method: 'DELETE' }),
  updatePage: (page: SourcePage['id'], text: string) => request<SourcePage>(`/pages/${page}/`, { method: 'PATCH', body: { text } }),
  createRegion: (body: Omit<Region, 'id'>) => request<Region>('/regions/', { method: 'POST', body }),
  updateRegion: (region: Region['id'], body: Partial<Region>) => request<Region>(`/regions/${region}/`, { method: 'PATCH', body }),
  conversations: (course: Course['id'], signal?: AbortSignal) => request<Conversation[]>(`/conversations/?course=${course}`, { signal }),
  createConversation: (course: Course['id'], title = 'Course questions') => request<Conversation>('/conversations/', { method: 'POST', body: { course, title } }),
  messages: (conversation: Conversation['id'], signal?: AbortSignal) => request<Message[]>(`/conversations/${conversation}/messages/`, { signal }),
  sendMessage: (conversation: Conversation['id'], body: { content: string; region_ids: Region['id'][]; context?: Message['context'] }) =>
    request<{ message: Message; job: Job }>(`/conversations/${conversation}/messages/`, { method: 'POST', body }),
  streamUrl: (conversation: Conversation['id'], job: Job['id']) => `${API_ROOT}/conversations/${conversation}/stream/?job=${job}`,
  lessons: (course: Course['id'], signal?: AbortSignal) => request<Lesson[]>(`/lessons/?course=${course}`, { signal }),
  deleteLesson: (lesson: Lesson['id']) => request<void>(`/lessons/${lesson}/`, { method: 'DELETE' }),
  createLesson: (body: { course: Course['id']; title: string; prompt: string; target_minutes: 1 | 2 | 3 | 10 | 15 | 20; region_ids?: Region['id'][]; purpose?: 'followup'; context?: Message['context'] }) => request<{ id?: Lesson['id']; lesson?: Lesson; job: Job }>('/lessons/', { method: 'POST', body }),
  reviseLesson: (lesson: Lesson['id'], body: { prompt: string; target_minutes: 10 | 15 | 20; region_ids?: Region['id'][] }) => request<{ job: Job }>(`/lessons/${lesson}/revisions/`, { method: 'POST', body }),
  saveLessonRevision: (lesson: Lesson['id'], body: { spec: Lesson['revisions'][number]['spec']; citations: Lesson['revisions'][number]['citations']; teaching_plan?: TeachingPlan | null }) => request<Lesson['revisions'][number]>(`/lessons/${lesson}/revisions/`, { method: 'POST', body }),
  validateTeachingPlan: (course: Course['id'], body: { revision_id: Lesson['revisions'][number]['id'] } | { spec: Lesson['revisions'][number]['spec']; teaching_plan: TeachingPlan | null }, signal?: AbortSignal) => request<TeachingPlanReport>(`/courses/${course}/teaching-plan/validate/`, { method: 'POST', body, signal }),
  renderLesson: (lesson: Lesson['id'], revision_id: number | string) => request<{ job: Job }>(`/lessons/${lesson}/render/`, { method: 'POST', body: { revision_id } }),
  jobs: (course: Course['id'], signal?: AbortSignal) => request<Job[]>(`/jobs/?course=${course}`, { signal }),
  cancelJob: (job: Job['id']) => request<Job>(`/jobs/${job}/cancel/`, { method: 'POST' }),
  retryJob: (job: Job['id']) => request<Job>(`/jobs/${job}/retry/`, { method: 'POST' }),
  studyItems: (course: Course['id'], signal?: AbortSignal) => request<StudyItem[]>(`/study-items/?course=${course}`, { signal }),
  createStudyItem: (body: Omit<StudyItem, 'id'>) => request<StudyItem>('/study-items/', { method: 'POST', body }),
  updateStudyItem: (item: StudyItem['id'], body: Partial<StudyItem>) => request<StudyItem>(`/study-items/${item}/`, { method: 'PATCH', body }),
  deleteStudyItem: (item: StudyItem['id']) => request<void>(`/study-items/${item}/`, { method: 'DELETE' }),
}

export async function loadCourseBundle(course: Course['id'], signal: AbortSignal): Promise<CourseBundle> {
  const [sources, conversations, lessons, jobs, studyItems] = await Promise.all([
    api.sources(course, signal),
    api.conversations(course, signal),
    api.lessons(course, signal),
    api.jobs(course, signal),
    api.studyItems(course, signal),
  ])
  return { sources, conversations, lessons, jobs, studyItems }
}

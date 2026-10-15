import { useCallback, useEffect, useRef, useState } from 'react'
import {
  IconActivity,
  IconBook2,
  IconBooks,
  IconChevronLeft,
  IconDownload,
  IconFileText,
  IconLayoutSidebarLeftCollapse,
  IconPlus,
  IconSchool,
  IconTrash,
  IconWifiOff,
} from './icons'
import { ChatPanel } from './components/ChatPanel'
import { JobsPanel } from './components/JobsPanel'
import { LessonStudio } from './components/LessonStudio'
import { SourceWorkspace } from './components/SourceWorkspace'
import { StudyTools } from './components/StudyTools'
import { ConfirmDialog } from './components/ConfirmDialog'
import { api, loadCourseBundle } from './lib/api'
import { bundleForDemoCourse, demoCourses, demoStatus } from './data/demo'
import type { CitationTarget, Course, CourseBundle, Job, Region, ServiceStatus, VideoContext } from './types'

const demoMode = new URLSearchParams(window.location.search).get('demo') === '1'
  || import.meta.env.VITE_DEMO_MODE === 'true'
const initialCourse = new URLSearchParams(window.location.search).get('course')
const initialRevisionText = new URLSearchParams(window.location.search).get('revision')
const initialRevision = initialRevisionText && /^\d+$/.test(initialRevisionText) && Number.isSafeInteger(Number(initialRevisionText)) && Number(initialRevisionText) > 0
  ? Number(initialRevisionText) : undefined

const emptyBundle: CourseBundle = { sources: [], conversations: [], lessons: [], jobs: [], studyItems: [] }

export default function App() {
  const [courses, setCourses] = useState<Course[]>(demoMode ? demoCourses : [])
  const [activeCourseId, setActiveCourseId] = useState<Course['id'] | undefined>(demoMode ? demoCourses[0].id : undefined)
  const [status, setStatus] = useState<ServiceStatus | undefined>(demoMode ? demoStatus : undefined)
  const [loading, setLoading] = useState(!demoMode)
  const [error, setError] = useState<string | undefined>()
  const [online, setOnline] = useState(navigator.onLine)
  const [railOpen, setRailOpen] = useState(true)
  const [notice, setNotice] = useState<string | undefined>()

  useEffect(() => {
    const onOnline = () => setOnline(true)
    const onOffline = () => setOnline(false)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  }, [])

  useEffect(() => {
    if (demoMode) return
    const controller = new AbortController()
    let current = true
    setLoading(true)
    Promise.all([api.courses(controller.signal), api.status(controller.signal)])
      .then(([nextCourses, nextStatus]) => {
        if (!current) return
        setCourses(nextCourses)
        setStatus(nextStatus)
        setActiveCourseId((selected) => selected ?? nextCourses.find((course) => String(course.id) === initialCourse)?.id ?? nextCourses[0]?.id)
        setError(undefined)
      })
      .catch((nextError) => {
        if (current && nextError instanceof Error && nextError.name !== 'AbortError') setError(nextError.message)
      })
      .finally(() => { if (current) setLoading(false) })
    return () => {
      current = false
      controller.abort()
    }
  }, [])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(undefined), 5000)
    return () => window.clearTimeout(timer)
  }, [notice])

  const activeCourse = courses.find((course) => course.id === activeCourseId)

  const createCourse = async (name: string) => {
    if (demoMode) {
      setNotice('The public demo does not create or save courses.')
      return
    }
    try {
      const created = await api.createCourse({ name, description: '' })
      setCourses((items) => [...items, created])
      setActiveCourseId(created.id)
    } catch (nextError) {
      setNotice(nextError instanceof Error ? nextError.message : 'Course could not be created.')
    }
  }

  if (loading) return <AppLoading />

  return (
    <div className={`app-shell ${railOpen ? '' : 'rail-collapsed'}`}>
      <a className="skip-link" href="#main-workspace">Skip to workspace</a>
      <CourseRail courses={courses} activeCourseId={activeCourseId} open={railOpen} demo={demoMode} onSelect={setActiveCourseId} onCreate={(name) => void createCourse(name)} />

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button rail-toggle" type="button" aria-label={railOpen ? 'Collapse course sidebar' : 'Expand course sidebar'} aria-expanded={railOpen} onClick={() => setRailOpen((value) => !value)}>
              {railOpen ? <IconLayoutSidebarLeftCollapse size={20} /> : <IconChevronLeft size={20} />}
            </button>
            <div><strong>{activeCourse?.name ?? 'TLDR study workspace'}</strong><span>{activeCourse?.description || 'Local, visual, and grounded in your sources.'}</span></div>
          </div>
          <div className="topbar-status">
            {!online && <span className="offline-badge"><IconWifiOff size={15} aria-hidden="true" /> Offline</span>}
            {demoMode && <span className="demo-badge">Public demo. No API or uploads.</span>}
            {!demoMode && status && <span className={status.generation_enabled ? 'service-badge ready' : 'service-badge'}>{status.generation_enabled ? `${status.provider} configured` : 'Local tools only'}</span>}
          </div>
        </header>

        {error && !activeCourse ? (
          <ServiceError message={error} />
        ) : !activeCourse ? (
          <FirstCourse onCreate={(name) => void createCourse(name)} />
        ) : (
          <CourseWorkspace key={String(activeCourse.id)} course={activeCourse} status={status} demo={demoMode} onStatusChange={setStatus} onNotice={setNotice} onCourseDeleted={() => {
            const remaining = courses.filter((entry) => entry.id !== activeCourse.id)
            setCourses(remaining)
            setActiveCourseId(remaining[0]?.id)
          }} />
        )}
      </div>
      {notice && <div className="toast" role="status">{notice}</div>}
    </div>
  )
}

function CourseWorkspace({ course, status, demo, onStatusChange, onNotice, onCourseDeleted }: { course: Course; status?: ServiceStatus; demo: boolean; onStatusChange: (status: ServiceStatus) => void; onNotice: (message: string) => void; onCourseDeleted: () => void }) {
  const [bundle, setBundle] = useState<CourseBundle>(demo ? bundleForDemoCourse(course.id) : emptyBundle)
  const [loading, setLoading] = useState(!demo)
  const [error, setError] = useState<string | undefined>()
  const initialLessonView = String(course.id) === initialCourse && initialRevision !== undefined
  const [tab, setTab] = useState<'sources' | 'lessons' | 'study'>(initialLessonView ? 'lessons' : 'sources')
  const [showJobs, setShowJobs] = useState(false)
  const [selectedRegionIds, setSelectedRegionIds] = useState<Region['id'][]>([])
  const [citationTarget, setCitationTarget] = useState<CitationTarget | undefined>()
  const [videoContext, setVideoContext] = useState<VideoContext | undefined>()
  const [focusRevisionId, setFocusRevisionId] = useState<string | number | undefined>(initialLessonView ? initialRevision : undefined)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const bundleRef = useRef(bundle)

  const load = useCallback((signal: AbortSignal) => loadCourseBundle(course.id, signal), [course.id])

  useEffect(() => {
    if (demo) {
      setBundle(bundleForDemoCourse(course.id))
      return
    }
    const controller = new AbortController()
    let current = true
    setLoading(true)
    setError(undefined)
    load(controller.signal)
      .then((next) => { if (current) { bundleRef.current = next; setBundle(next) } })
      .catch((nextError) => { if (current && nextError instanceof Error && nextError.name !== 'AbortError') setError(nextError.message) })
      .finally(() => { if (current) setLoading(false) })
    return () => {
      current = false
      controller.abort()
    }
  }, [course.id, demo, load])

  const refreshBundle = useCallback(async () => {
    if (demo) return
    const next = await loadCourseBundle(course.id, new AbortController().signal)
    const previous = bundleRef.current
    const completed = next.jobs.find((job) => job.status === 'complete' && previous.jobs.some((old) => old.id === job.id && ['queued', 'running', 'paused'].includes(old.status)))
    const revisionId = completed?.result?.revision_id
    if (typeof revisionId === 'string' || typeof revisionId === 'number') {
      setFocusRevisionId(revisionId)
      setTab('lessons')
    }
    bundleRef.current = next
    setBundle(next)
  }, [course.id, demo])

  useEffect(() => {
    if (demo || !bundle.jobs.some((job) => job.status === 'queued' || job.status === 'running')) return
    let current = true
    const run = () => void refreshBundle().catch(() => undefined)
    const poll = window.setInterval(() => { if (current) run() }, 3000)
    return () => { current = false; window.clearInterval(poll) }
  }, [bundle.jobs, demo, refreshBundle])

  useEffect(() => {
    const validRegionIds = new Set(bundle.sources.flatMap((source) => source.pages.flatMap((page) => page.regions.map((region) => region.id))))
    setSelectedRegionIds((items) => items.filter((id) => validRegionIds.has(id)))
  }, [bundle.sources])

  useEffect(() => {
    if (!videoContext) return
    const revisionExists = bundle.lessons.some((lesson) => lesson.revisions.some((revision) => revision.id === videoContext.revision_id))
    if (!revisionExists) setVideoContext(undefined)
  }, [bundle.lessons, videoContext])

  const pendingJobs = bundle.jobs.filter((job) => ['queued', 'running', 'paused'].includes(job.status)).length
  const toggleRegion = (id: Region['id']) => setSelectedRegionIds((items) => items.includes(id) ? items.filter((entry) => entry !== id) : [...items, id])
  const updateBundle = (update: (value: CourseBundle) => CourseBundle) => setBundle((value) => {
    const next = update(value)
    bundleRef.current = next
    return next
  })
  const addJob = (job: Job) => updateBundle((value) => ({ ...value, jobs: [job, ...value.jobs.filter((entry) => entry.id !== job.id)] }))
  const availableRefs = bundle.sources.flatMap((source) => source.pages.flatMap((page) => page.regions.map((region) => ({
    id: `r${region.id}`,
    regionId: region.id,
    label: `${source.title}, p. ${page.number}: ${region.label || 'marked region'}`,
  }))))

  const deleteCourse = async () => {
    if (demo) { onNotice('Demo courses are curated and cannot be removed.'); setConfirmDelete(false); return }
    setDeleting(true)
    try {
      await api.deleteCourse(course.id)
      onCourseDeleted()
      onNotice(`Removed ${course.name}.`)
    } catch (nextError) {
      onNotice(nextError instanceof Error ? nextError.message : 'Course could not be removed.')
    } finally { setDeleting(false) }
  }

  if (loading) return <WorkspaceLoading />
  if (error) return <ServiceError message={error} />

  return (
    <main id="main-workspace" className="course-workspace">
      <nav className="workspace-nav" aria-label="Course workspace sections">
        <div>
          <button className={tab === 'sources' ? 'workspace-tab active' : 'workspace-tab'} type="button" aria-current={tab === 'sources' ? 'page' : undefined} onClick={() => setTab('sources')}><IconFileText size={18} aria-hidden="true" /> Sources</button>
          <button className={tab === 'lessons' ? 'workspace-tab active' : 'workspace-tab'} type="button" aria-current={tab === 'lessons' ? 'page' : undefined} onClick={() => setTab('lessons')}><IconSchool size={18} aria-hidden="true" /> Lessons</button>
          <button className={tab === 'study' ? 'workspace-tab active' : 'workspace-tab'} type="button" aria-current={tab === 'study' ? 'page' : undefined} onClick={() => setTab('study')}><IconBooks size={18} aria-hidden="true" /> Study tools</button>
        </div>
        <div className="course-actions">
          <button className="activity-button" type="button" onClick={() => setShowJobs(true)}><IconActivity size={18} aria-hidden="true" /> Activity {pendingJobs > 0 && <span>{pendingJobs}</span>}</button>
          <a className="activity-button" href={demo ? undefined : api.exportCourseUrl(course.id)} onClick={(event) => { if (demo) { event.preventDefault(); onNotice('Course export is available in the local app.') } }}><IconDownload size={17} aria-hidden="true" /> Export</a>
          <button className="activity-button danger-ghost" type="button" onClick={() => setConfirmDelete(true)}><IconTrash size={17} aria-hidden="true" /> Remove course</button>
        </div>
      </nav>

      <div className="workspace-body">
        <div className="primary-pane">
          {tab === 'sources' && <SourceWorkspace courseId={course.id} sources={bundle.sources} demo={demo} citationTarget={citationTarget} selectedRegionIds={selectedRegionIds} onToggleRegion={toggleRegion} onSourcesChange={(sources) => updateBundle((value) => ({ ...value, sources }))} onRefresh={() => void refreshBundle()} onNotice={onNotice} />}
          {tab === 'lessons' && <LessonStudio courseId={course.id} lessons={bundle.lessons} sources={bundle.sources} demo={demo} availableRefs={availableRefs} focusRevisionId={focusRevisionId} onRefresh={() => void refreshBundle()} onLessonsChange={(lessons) => updateBundle((value) => ({ ...value, lessons }))} onJobCreated={addJob} onVideoContext={(context) => { setVideoContext(context); onNotice('Lesson moment attached to the course chat.') }} onNotice={onNotice} />}
          {tab === 'study' && <StudyTools courseId={course.id} items={bundle.studyItems} demo={demo} onItemsChange={(studyItems) => updateBundle((value) => ({ ...value, studyItems }))} onNotice={onNotice} />}
        </div>
        <ChatPanel courseId={course.id} courseName={course.name} conversations={bundle.conversations} jobs={bundle.jobs} demo={demo} generationEnabled={status?.generation_enabled} selectedRegionIds={selectedRegionIds} videoContext={videoContext} onClearVideoContext={() => setVideoContext(undefined)} onConversationsChange={(conversations) => updateBundle((value) => ({ ...value, conversations }))} onJobCreated={addJob} onCitation={(target) => { setCitationTarget(target); setTab('sources') }} onNotice={onNotice} />
      </div>
      {showJobs && <JobsPanel jobs={bundle.jobs} status={status} demo={demo} onClose={() => setShowJobs(false)} onJobsChange={(jobs) => updateBundle((value) => ({ ...value, jobs }))} onStatusChange={onStatusChange} onNotice={onNotice} />}
      {confirmDelete && <ConfirmDialog title={`Remove ${course.name}?`} message="This removes all sources, conversations, lessons, jobs, and study items in the course. This cannot be undone." requiredText={course.name} confirmLabel="Remove course" busy={deleting} onCancel={() => setConfirmDelete(false)} onConfirm={() => void deleteCourse()} />}
    </main>
  )
}

function CourseRail({ courses, activeCourseId, open, demo, onSelect, onCreate }: { courses: Course[]; activeCourseId?: Course['id']; open: boolean; demo: boolean; onSelect: (id: Course['id']) => void; onCreate: (name: string) => void }) {
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  return (
    <aside className="course-rail" aria-label="Courses" hidden={!open}>
      <div className="brand"><div className="brand-mark"><IconBook2 size={22} /></div><div><strong>TLDR</strong><span>Visual study desk</span></div></div>
      <div className="rail-heading"><span>Your courses</span><button className="icon-button" type="button" aria-label="Create course" onClick={() => setCreating(true)}><IconPlus size={18} /></button></div>
      <nav className="course-list">
        {courses.map((course, index) => <button className={course.id === activeCourseId ? 'course-link active' : 'course-link'} type="button" aria-current={course.id === activeCourseId ? 'page' : undefined} onClick={() => onSelect(course.id)} key={course.id}><span className="course-index">{String(index + 1).padStart(2, '0')}</span><span><strong>{course.name}</strong><small>{course.description || 'Course workspace'}</small></span></button>)}
      </nav>
      <div className="rail-foot"><span>{demo ? 'Curated local sample' : 'Files are stored locally. AI requests send relevant text and images to Gemini.'}</span></div>
      {creating && <div className="rail-create"><label>Course name<input autoFocus value={name} onChange={(event) => setName(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && name.trim()) { onCreate(name.trim()); setCreating(false); setName('') } }} /></label><div className="button-row"><button className="button compact" type="button" onClick={() => setCreating(false)}>Cancel</button><button className="button primary compact" type="button" disabled={!name.trim()} onClick={() => { onCreate(name.trim()); setCreating(false); setName('') }}>{demo ? 'Demo notice' : 'Create'}</button></div></div>}
    </aside>
  )
}

function AppLoading() {
  return <div className="app-loading" role="status"><div className="brand-mark"><IconBook2 size={25} /></div><strong>Opening your study desk</strong><span>Checking the local service and courses</span></div>
}

function WorkspaceLoading() {
  return <main className="workspace-loading" role="status"><div className="workspace-skeleton"><i /><i /><i /><i /></div><span>Loading course sources and study state</span></main>
}

function ServiceError({ message }: { message: string }) {
  return <main className="service-error"><IconWifiOff size={34} aria-hidden="true" /><h1>The local study service is unavailable</h1><p>{message}</p><p>Start the Django API and worker, then reload this page. The app will not invent responses while the service is offline.</p></main>
}

function FirstCourse({ onCreate }: { onCreate: (name: string) => void }) {
  const [name, setName] = useState('')
  return <main className="first-course"><IconBook2 size={38} aria-hidden="true" /><h1>Make a course workspace</h1><p>Sources, cited questions, visual lessons, and review tools stay grouped by course.</p><label>Course name<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Example: Introductory mechanics" /></label><button className="button primary" type="button" disabled={!name.trim()} onClick={() => onCreate(name.trim())}><IconPlus size={18} aria-hidden="true" /> Create course</button></main>
}

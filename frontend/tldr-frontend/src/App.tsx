import { useCallback, useEffect, useRef, useState } from 'react'
import {
  IconActivity,
  IconBook2,
  IconBooks,
  IconChevronLeft,
  IconDownload,
  IconFileText,
  IconLayoutSidebarLeftCollapse,
  IconMovie,
  IconPlus,
  IconTrash,
  IconWifiOff,
} from './icons'
import { ChatPanel, type ChatAttachmentRequest } from './components/ChatPanel'
import { JobsPanel } from './components/JobsPanel'
import { LessonStudio } from './components/LessonStudio'
import { SourceWorkspace } from './components/SourceWorkspace'
import { StudyTools } from './components/StudyTools'
import { ConfirmDialog } from './components/ConfirmDialog'
import { StudySidebar, type StudySidebarTab, type ReadingSelection } from './components/NotesMargin'
import { TextbookOutline } from './components/TextbookOutline'
import { CourseSidebar } from './components/CourseSidebar'
import type { SceneReferences } from './lib/sceneSources'
import { api, loadCourseBundle } from './lib/api'
import { bundleForDemoCourse, demoCourses, demoStatus } from './data/demo'
import type { CitationTarget, Course, CourseBundle, Job, Region, ServiceStatus } from './types'

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
  const [narrow, setNarrow] = useState(() => window.matchMedia('(max-width: 899px)').matches)
  const [railOpen, setRailOpen] = useState(() => {
    try {
      const saved = localStorage.getItem('tldr-sidebar-open')
      if (saved === 'true' || saved === 'false') return saved === 'true'
    } catch { /* Use the viewport default when storage is unavailable. */ }
    return !window.matchMedia('(max-width: 899px)').matches
  })
  const railToggleRef = useRef<HTMLButtonElement>(null)
  const closeSidebar = useCallback(() => {
    setRailOpen(false)
    window.requestAnimationFrame(() => railToggleRef.current?.focus())
  }, [])
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try { return localStorage.getItem('tldr-theme') === 'dark' ? 'dark' : 'light' }
    catch { return 'light' }
  })
  const [notice, setNotice] = useState<string | undefined>()

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
    try { localStorage.setItem('tldr-theme', theme) } catch { /* Keep the session usable when storage is unavailable. */ }
  }, [theme])

  useEffect(() => {
    const syncAppearance = (event: StorageEvent) => {
      if (event.key === 'tldr-theme' && (event.newValue === 'light' || event.newValue === 'dark')) setTheme(event.newValue)
    }
    window.addEventListener('storage', syncAppearance)
    return () => window.removeEventListener('storage', syncAppearance)
  }, [])

  useEffect(() => {
    try { localStorage.setItem('tldr-sidebar-open', String(railOpen)) } catch { /* Session state still works. */ }
  }, [railOpen])

  useEffect(() => {
    const query = window.matchMedia('(max-width: 899px)')
    const update = () => setNarrow(query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    const closeMenu = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || event.defaultPrevented) return
      const menu = Array.from(document.querySelectorAll<HTMLDetailsElement>('details[open]')).find((element) => element.getClientRects().length && (element.matches('.course-more, .source-actions-menu') || element.contains(document.activeElement)))
      const modal = Array.from(document.querySelectorAll<HTMLElement>('[role="dialog"], [role="alertdialog"], dialog[open]')).find((element) => element.getClientRects().length)
      if (modal && (!menu || !modal.contains(menu))) return
      if (menu) { menu.open = false; menu.querySelector('summary')?.focus(); event.preventDefault(); event.stopPropagation() }
    }
    document.addEventListener('keydown', closeMenu, true)
    return () => document.removeEventListener('keydown', closeMenu, true)
  }, [])

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
      if (narrow) closeSidebar()
    } catch (nextError) {
      setNotice(nextError instanceof Error ? nextError.message : 'Course could not be created.')
    }
  }

  if (loading) return <AppLoading />

  return (
    <div className={`app-shell theme-${theme} ${railOpen ? '' : 'rail-collapsed'}`}>
      <a className="skip-link" href="#main-workspace">Skip to workspace</a>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-left">
            <button ref={railToggleRef} className="icon-button rail-toggle" type="button" disabled={!activeCourse} aria-controls="course-outline" aria-label={railOpen ? 'Collapse course sidebar' : 'Expand course sidebar'} aria-expanded={railOpen} onClick={() => setRailOpen((value) => !value)}>
              {railOpen ? <IconLayoutSidebarLeftCollapse size={20} /> : <IconChevronLeft size={20} />}
            </button>
            <span className="topbar-brand" aria-label="TLDR home">TLDR</span>
            <div><strong>{activeCourse?.name ?? 'TLDR study workspace'}</strong><span>{activeCourse?.description || 'Local, visual, and grounded in your sources.'}</span></div>
          </div>
          <div className="topbar-status">
            <div className="theme-options" role="group" aria-label="Appearance">
              <button type="button" aria-pressed={theme === 'light'} onClick={() => setTheme('light')}>Light</button>
              <button type="button" aria-pressed={theme === 'dark'} onClick={() => setTheme('dark')}>Dark</button>
            </div>
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
          <CourseWorkspace key={String(activeCourse.id)} course={activeCourse} courses={courses} sidebarOpen={railOpen} narrow={narrow} onCloseSidebar={closeSidebar} status={status} demo={demoMode} onSelectCourse={(id) => { setActiveCourseId(id); if (narrow) closeSidebar() }} onCreateCourse={(name) => void createCourse(name)} onStatusChange={setStatus} onNotice={setNotice} onCourseDeleted={() => {
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

function CourseWorkspace({ course, courses, sidebarOpen, narrow, onCloseSidebar, status, demo, onSelectCourse, onCreateCourse, onStatusChange, onNotice, onCourseDeleted }: { course: Course; courses: Course[]; sidebarOpen: boolean; narrow: boolean; onCloseSidebar: () => void; status?: ServiceStatus; demo: boolean; onSelectCourse: (id: Course['id']) => void; onCreateCourse: (name: string) => void; onStatusChange: (status: ServiceStatus) => void; onNotice: (message: string) => void; onCourseDeleted: () => void }) {
  const [bundle, setBundle] = useState<CourseBundle>(demo ? bundleForDemoCourse(course.id) : emptyBundle)
  const [loading, setLoading] = useState(!demo)
  const [error, setError] = useState<string | undefined>()
  const initialLessonView = String(course.id) === initialCourse && initialRevision !== undefined
  const [tab, setTab] = useState<'sources' | 'lessons' | 'study'>(initialLessonView ? 'lessons' : 'sources')
  const initialWorkspaceResolved = useRef(initialLessonView)
  const [showJobs, setShowJobs] = useState(false)
  const [chatOpen, setChatOpen] = useState(true)
  const [marginTab, setMarginTab] = useState<StudySidebarTab>('sources')
  const [readingSelection, setReadingSelection] = useState<ReadingSelection>()
  const [sourceNavigation, setSourceNavigation] = useState<{ sourceId: CourseBundle['sources'][number]['id']; pageIndex: number }>()
  const updateReadingSelection = useCallback((next: ReadingSelection) => setReadingSelection((current) => current?.sourceId === next.sourceId && current?.pageId === next.pageId ? current : next), [])
  const [selectedRegionIds, setSelectedRegionIds] = useState<Region['id'][]>([])
  const [citationTarget, setCitationTarget] = useState<CitationTarget | undefined>()
  const [attachmentRequest, setAttachmentRequest] = useState<ChatAttachmentRequest>()
  const attachmentSequence = useRef(0)
  const [sceneReferences, setSceneReferences] = useState<SceneReferences>()
  const attachToTutor = (attachment: Omit<ChatAttachmentRequest, 'id'>) => {
    setAttachmentRequest({ ...attachment, id: ++attachmentSequence.current })
    setMarginTab('tutor')
    setChatOpen(true)
  }
  const [focusRevisionId, setFocusRevisionId] = useState<string | number | undefined>(initialLessonView ? initialRevision : undefined)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const bundleRef = useRef(bundle)
  const viewRefs = useRef<Record<'sources' | 'lessons' | 'study', HTMLDivElement | null>>({ sources: null, lessons: null, study: null })
  const viewScroll = useRef<Record<'sources' | 'lessons' | 'study', number>>({ sources: 0, lessons: 0, study: 0 })
  const documentScroll = useRef<Record<'sources' | 'lessons' | 'study', number>>({ sources: 0, lessons: 0, study: 0 })

  const activateTab = (next: 'sources' | 'lessons' | 'study') => {
    if (next === tab) return
    const currentView = viewRefs.current[tab]
    if (currentView) viewScroll.current[tab] = currentView.scrollTop
    const documentScrolling = window.matchMedia('(max-width: 899px)').matches
    if (documentScrolling) documentScroll.current[tab] = window.scrollY
    setTab(next)
    window.requestAnimationFrame(() => {
      const nextView = viewRefs.current[next]
      if (nextView) nextView.scrollTop = viewScroll.current[next]
      if (documentScrolling) window.scrollTo(0, documentScroll.current[next])
    })
  }

  const openSource = (sourceId: CourseBundle['sources'][number]['id'], pageIndex?: number) => {
    const source = bundle.sources.find((entry) => entry.id === sourceId)
    const selectedPage = sourceId === readingSelection?.sourceId
      ? source?.pages.findIndex((page) => page.id === readingSelection.pageId) ?? 0
      : 0
    setSourceNavigation({ sourceId, pageIndex: pageIndex ?? Math.max(0, selectedPage) })
    activateTab('sources')
    if (narrow) onCloseSidebar()
  }

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

  useEffect(() => {
    if (loading || initialWorkspaceResolved.current) return
    initialWorkspaceResolved.current = true
    if (bundle.lessons.some((item) => item.revisions.length > 0)) setTab('lessons')
  }, [bundle.lessons, loading])

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

  const pendingJobs = bundle.jobs.filter((job) => ['queued', 'running', 'paused'].includes(job.status)).length
  const toggleRegion = (id: Region['id']) => {
    const regionIds = selectedRegionIds.includes(id) ? selectedRegionIds.filter((entry) => entry !== id) : [...selectedRegionIds, id]
    setSelectedRegionIds(regionIds)
    attachToTutor({ regionIds })
  }
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

  const sidebar = <CourseSidebar open={sidebarOpen} narrow={narrow} onClose={onCloseSidebar}>
    <TextbookOutline courses={courses} activeCourseId={course.id} sources={bundle.sources} sourceId={readingSelection?.sourceId ?? bundle.sources[0]?.id} pageId={readingSelection?.pageId} onClose={onCloseSidebar} onSelectCourse={onSelectCourse} onCreateCourse={onCreateCourse} onSelectSource={openSource} onSelectPage={openSource} onOpenStudy={() => { activateTab('study'); if (narrow) onCloseSidebar() }} />
  </CourseSidebar>

  return (
    <main id="main-workspace" className={`course-workspace workspace-${tab}`} data-workspace={tab} aria-busy={loading}>
      <nav className="workspace-nav" aria-label="Course workspace sections">
        <div>
          <button className={tab === 'lessons' ? 'workspace-tab active' : 'workspace-tab'} type="button" aria-current={tab === 'lessons' ? 'page' : undefined} onClick={() => activateTab('lessons')}><IconMovie size={18} aria-hidden="true" /> Video</button>
          <button className={tab === 'sources' ? 'workspace-tab active' : 'workspace-tab'} type="button" aria-current={tab === 'sources' ? 'page' : undefined} onClick={() => activateTab('sources')}><IconFileText size={18} aria-hidden="true" /> Notes</button>
          <button className={tab === 'study' ? 'workspace-tab active' : 'workspace-tab'} type="button" aria-current={tab === 'study' ? 'page' : undefined} onClick={() => activateTab('study')}><IconBooks size={18} aria-hidden="true" /> Study tools</button>
        </div>
        <div className="course-actions">
          <button className="activity-button tutor-toggle" type="button" aria-controls="study-sidebar" aria-expanded={chatOpen} onClick={() => setChatOpen((value) => !value)}><IconBook2 size={17} aria-hidden="true" /> {chatOpen ? 'Hide study sidebar' : 'Show study sidebar'}</button>
          <button className="activity-button" type="button" onClick={() => setShowJobs(true)}><IconActivity size={18} aria-hidden="true" /> Activity {pendingJobs > 0 && <span>{pendingJobs}</span>}</button>
          <details className="course-more"><summary className="activity-button">Course</summary><div><a className="activity-button" href={demo ? undefined : api.exportCourseUrl(course.id)} onClick={(event) => { if (demo) { event.preventDefault(); onNotice('Course export is available in the local app.') } }}><IconDownload size={17} aria-hidden="true" /> Export</a><button className="activity-button danger-ghost" type="button" onClick={() => setConfirmDelete(true)}><IconTrash size={17} aria-hidden="true" /> Remove course</button></div></details>
        </div>
      </nav>

      <div className="course-study-layout">
        {sidebar}
        {loading ? <WorkspaceLoading /> : error ? <ServiceError message={error} /> : <div className={`workspace-body ${chatOpen ? '' : 'chat-collapsed'}`}>
        <div className="primary-pane">
          <div ref={(node) => { viewRefs.current.sources = node }} className="workspace-view notes-view" hidden={tab !== 'sources'}>
            <SourceWorkspace active={tab === 'sources'} courseId={course.id} sources={bundle.sources} demo={demo} citationTarget={citationTarget} navigationTarget={sourceNavigation} selectedRegionIds={selectedRegionIds} onReadingSelection={updateReadingSelection} onToggleRegion={toggleRegion} onSourcesChange={(sources) => updateBundle((value) => ({ ...value, sources }))} onRefresh={() => void refreshBundle()} onNotice={onNotice} />
          </div>
          <div ref={(node) => { viewRefs.current.lessons = node }} className="workspace-view video-view" hidden={tab !== 'lessons'}>
            <LessonStudio active={tab === 'lessons'} courseId={course.id} lessons={bundle.lessons} sources={bundle.sources} demo={demo} availableRefs={availableRefs} focusRevisionId={focusRevisionId} onRefresh={() => void refreshBundle()} onLessonsChange={(lessons) => updateBundle((value) => ({ ...value, lessons }))} onJobCreated={addJob} onSceneReferences={setSceneReferences} onVideoContext={(videoContext) => { attachToTutor({ videoContext }); onNotice('Lesson moment attached to the course chat.') }} onNotice={onNotice} />
          </div>
          <div ref={(node) => { viewRefs.current.study = node }} className="workspace-view study-view" hidden={tab !== 'study'}>
            <StudyTools courseId={course.id} items={bundle.studyItems} demo={demo} onItemsChange={(studyItems) => updateBundle((value) => ({ ...value, studyItems }))} onNotice={onNotice} />
          </div>
        </div>
        <div id="study-sidebar" className="chat-slot study-sidebar notes-margin" hidden={!chatOpen}>
          <StudySidebar mode={tab} tab={marginTab} onTab={setMarginTab} sources={bundle.sources} selection={readingSelection} sceneReferences={sceneReferences} studyItems={bundle.studyItems} onCitation={(target) => { setCitationTarget(target); activateTab('sources') }} onOpenStudy={() => activateTab('study')}>
            <ChatPanel active={chatOpen && marginTab === 'tutor'} attachmentRequest={attachmentRequest} courseId={course.id} courseName={course.name} conversations={bundle.conversations} jobs={bundle.jobs} demo={demo} generationEnabled={status?.generation_enabled} onRegionSelectionChange={setSelectedRegionIds} onConversationCreated={(conversation) => updateBundle((value) => ({ ...value, conversations: [...value.conversations.filter((entry) => entry.id !== conversation.id), conversation] }))} onJobCreated={addJob} onCitation={(target) => { setCitationTarget(target); activateTab('sources') }} onNotice={onNotice} />
          </StudySidebar>
        </div>
      </div>}
      </div>
      {showJobs && <JobsPanel jobs={bundle.jobs} status={status} demo={demo} onClose={() => setShowJobs(false)} onJobsChange={(jobs) => updateBundle((value) => ({ ...value, jobs }))} onStatusChange={onStatusChange} onNotice={onNotice} />}
      {confirmDelete && <ConfirmDialog title={`Remove ${course.name}?`} message="This removes all sources, conversations, lessons, jobs, and study items in the course. This cannot be undone." requiredText={course.name} confirmLabel="Remove course" busy={deleting} onCancel={() => setConfirmDelete(false)} onConfirm={() => void deleteCourse()} />}
    </main>
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

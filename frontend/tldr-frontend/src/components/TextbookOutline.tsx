import { useEffect, useRef, useState } from 'react'
import {
  IconBook2,
  IconBooks,
  IconChevronDown,
  IconFileText,
  IconPhoto,
  IconPlus,
  IconX,
} from '../icons'
import type { Course, Source, SourcePage } from '../types'
import './textbook-outline.css'

type Props = {
  courses: Course[]
  activeCourseId: Course['id']
  sources: Source[]
  sourceId?: Source['id']
  pageId?: SourcePage['id']
  onSelectCourse: (courseId: Course['id']) => void
  onCreateCourse: (name: string) => void
  onSelectSource: (sourceId: Source['id']) => void
  onSelectPage: (sourceId: Source['id'], pageIndex: number) => void
  onOpenStudy: () => void
  onClose?: () => void
}

const pageHeading = (page: SourcePage) => {
  const match = page.text.match(/^\s*#{1,6}\s+([^\n#]+)/m)
  return match?.[1].trim().replace(/[*_`]/g, '')
}

export function TextbookOutline({ courses, activeCourseId, sources, sourceId, pageId, onSelectCourse, onCreateCourse, onSelectSource, onSelectPage, onOpenStudy, onClose }: Props) {
  const [creating, setCreating] = useState(false)
  const [courseName, setCourseName] = useState('')
  const [courseExpanded, setCourseExpanded] = useState(true)
  const [expandedSourceId, setExpandedSourceId] = useState<Source['id'] | undefined>(sourceId)
  const currentPageRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    currentPageRef.current?.scrollIntoView({ block: 'nearest' })
  }, [pageId])

  useEffect(() => {
    setExpandedSourceId(sourceId)
  }, [sourceId])

  const createCourse = () => {
    const name = courseName.trim()
    if (!name) return
    onCreateCourse(name)
    setCourseName('')
    setCreating(false)
  }

  const sourceFor = (kinds: string[]) => sources.find((entry) => kinds.includes(entry.kind.toLowerCase()))
  const libraryItems = [
    { label: 'PDFs', icon: IconFileText, source: sourceFor(['pdf']) },
    { label: 'Images', icon: IconPhoto, source: sourceFor(['image']) },
    { label: 'Notes & websites', icon: IconBook2, source: sourceFor(['text', 'web']) },
  ]

  return (
    <aside id="course-outline" className="textbook-outline" aria-label="Course and page outline">
      <div className="outline-heading">
        <h2>My Courses</h2>
        <div className="outline-heading-actions"><button type="button" aria-label="Create course" aria-expanded={creating} onClick={() => setCreating((value) => !value)}><IconPlus size={16} aria-hidden="true" /></button>{onClose && <button type="button" aria-label="Close course sidebar" onClick={onClose}><IconX size={16} aria-hidden="true" /></button>}</div>
      </div>

      {creating && <form className="outline-create" onSubmit={(event) => { event.preventDefault(); createCourse() }}>
        <label htmlFor="outline-course-name">Course name</label>
        <input id="outline-course-name" autoFocus value={courseName} onChange={(event) => setCourseName(event.target.value)} />
        <div><button type="button" onClick={() => { setCreating(false); setCourseName('') }}>Cancel</button><button type="submit" disabled={!courseName.trim()}>Create</button></div>
      </form>}

      <nav className="outline-courses" aria-label="My courses">
        {courses.map((course) => {
          const current = course.id === activeCourseId
          const expanded = current && courseExpanded
          return <div className={expanded ? 'outline-course current expanded' : current ? 'outline-course current' : 'outline-course'} key={course.id}>
            <button className="outline-course-button" type="button" aria-current={current ? 'page' : undefined} aria-expanded={expanded} onClick={() => { if (current) setCourseExpanded((value) => !value); else onSelectCourse(course.id) }}>
              <IconBook2 size={16} aria-hidden="true" />
              <span>{course.name}</span>
              <IconChevronDown className="outline-caret" size={14} aria-hidden="true" />
            </button>
            {expanded && <div className="outline-sources">
              {sources.length === 0 && <p className="outline-empty">No sources yet</p>}
              {sources.map((entry, sourceIndex) => {
                const selected = entry.id === sourceId
                const sourceExpanded = selected && expandedSourceId === entry.id
                return <div className={sourceExpanded ? 'outline-source selected expanded' : selected ? 'outline-source selected' : 'outline-source'} key={entry.id}>
                  <button type="button" aria-current={selected ? 'location' : undefined} aria-expanded={sourceExpanded} onClick={() => {
                    if (selected) setExpandedSourceId((value) => value === entry.id ? undefined : entry.id)
                    else { setExpandedSourceId(entry.id); onSelectSource(entry.id) }
                  }}>
                    <span className="outline-number">{sourceIndex + 1}</span>
                    <span>{entry.title}</span>
                    {entry.pages.length > 0 && <IconChevronDown className="outline-source-caret" size={13} aria-hidden="true" />}
                  </button>
                  {sourceExpanded && entry.pages.length > 0 && <div className="outline-pages" aria-label={`${entry.title} pages`}>
                    {entry.pages.map((entryPage, pageIndex) => {
                      const currentPage = entryPage.id === pageId
                      const heading = pageHeading(entryPage)
                      return <button ref={currentPage ? currentPageRef : undefined} type="button" className={currentPage ? 'current' : undefined} aria-current={currentPage ? 'page' : undefined} onClick={() => onSelectPage(entry.id, pageIndex)} key={entryPage.id}>
                        <span>{entryPage.number}</span>
                        <span>{heading || `Page ${entryPage.number}`}</span>
                      </button>
                    })}
                  </div>}
                </div>
              })}
            </div>}
          </div>
        })}
      </nav>

      <div className="outline-library">
        <h2>Library</h2>
        {libraryItems.map(({ label, icon: Icon, source: librarySource }) => <button type="button" disabled={!librarySource} title={librarySource ? `Open ${librarySource.title}` : `No ${label.toLowerCase()} in this course`} onClick={() => { if (librarySource) onSelectSource(librarySource.id) }} key={label}><Icon size={16} aria-hidden="true" /><span>{label}</span></button>)}
        <button type="button" onClick={onOpenStudy}><IconBooks size={16} aria-hidden="true" /><span>Flashcards</span></button>
      </div>
    </aside>
  )
}

import { useState, type ReactNode } from 'react'
import { IconFileText, IconMessageCircle } from '../icons'
import type { CitationTarget, Source, SourcePage, StudyItem } from '../types'
import { MathText } from './MathText'
import type { SceneReferences } from '../lib/sceneSources'
import './notes-margin.css'

export type StudySidebarTab = 'sources' | 'tutor' | 'flashcards'
export type ReadingSelection = { sourceId: Source['id']; pageId?: SourcePage['id'] }

export function StudySidebar({ mode, children, tab, onTab, sources, selection, sceneReferences, studyItems, onCitation, onOpenStudy }: {
  mode: 'sources' | 'lessons' | 'study'
  children: ReactNode
  tab: StudySidebarTab
  onTab: (tab: StudySidebarTab) => void
  sources: Source[]
  selection?: ReadingSelection
  sceneReferences?: SceneReferences
  studyItems: StudyItem[]
  onCitation: (target: CitationTarget) => void
  onOpenStudy: () => void
}) {
  const source = sources.find((entry) => entry.id === selection?.sourceId) ?? sources[0]
  const page = source?.pages.find((entry) => entry.id === selection?.pageId) ?? source?.pages[0]
  const cards = studyItems.filter((item) => item.kind === 'flashcard')
  return <>
    <nav className="notes-margin-tabs" aria-label="Study sidebar tabs">
      {(['sources', 'tutor', 'flashcards'] as const).map((value) => <button type="button" aria-pressed={tab === value} onClick={() => onTab(value)} key={value}>{value === 'sources' ? 'Sources' : value === 'tutor' ? 'Tutor' : 'Flashcards'}</button>)}
    </nav>
    <section className="notes-margin-content" aria-label="Study sources" hidden={tab !== 'sources'}>
      {mode !== 'sources' ? <>
        {mode === 'lessons' && sceneReferences?.citations.length ? <>
          <p className="margin-context-title">Sources for {sceneReferences.title}</p>
          <ol className="margin-sources">{sceneReferences.citations.map((citation, index) => <li key={`${citation.page_id}:${citation.region_id ?? ''}`}>
            <span className="margin-source-number">{index + 1}</span><IconFileText size={19} aria-hidden="true" />
            <div><button type="button" className="margin-source-link" onClick={() => onCitation({ sourceId: citation.source_id, pageId: citation.page_id, regionId: citation.region_id })}>{citation.source_title}</button><p>Page {citation.page_number}{citation.region_id !== undefined ? ' · Marked region' : ''}</p>{citation.quote && <q><MathText text={citation.quote} /></q>}</div>
          </li>)}</ol>
          <details className="margin-other-sources"><summary>All course sources</summary><CourseSources sources={sources} onCitation={onCitation} /></details>
        </> : <>
          <h2 className="margin-context-title">Course sources</h2>
          {mode === 'lessons' && <p className="margin-empty">No source references are recorded for the current scene. These are the course's imported materials.</p>}
          <CourseSources sources={sources} onCitation={onCitation} />
        </>}
      </> : source && page ? <>
        <ol className="margin-sources">
          <li>
            <span className="margin-source-number">1</span><IconFileText size={19} aria-hidden="true" />
            <div><button className="margin-source-link" type="button" onClick={() => onCitation({ sourceId: source.id, pageId: page.id })}>{source.title}</button>
              <p>Page {page.number} of {source.pages.length} · {source.kind === 'web' ? 'Webpage' : source.kind.toUpperCase()}</p>
              {(source.fetched_url || source.source_url || source.original_url) && <a href={source.fetched_url || source.source_url || source.original_url} target="_blank" rel="noopener noreferrer">Open original {source.kind === 'web' ? 'website' : 'file'}</a>}
            </div>
          </li>
          {page.regions.map((region, index) => <li key={region.id}>
            <span className="margin-source-number">{index + 2}</span><IconFileText size={19} aria-hidden="true" />
            <div><button className="margin-source-link" type="button" onClick={() => onCitation({ sourceId: source.id, pageId: page.id, regionId: region.id })}>{region.label || `Marked region ${index + 1}`}</button><p>From {source.title}, page {page.number}.</p>{region.text && <q><MathText text={region.text} /></q>}</div>
          </li>)}
        </ol>
        {sources.length > 1 && <details className="margin-other-sources"><summary>Other course sources</summary>{sources.filter((entry) => entry.id !== source.id).map((entry) => <button type="button" disabled={!entry.pages.length} onClick={() => onCitation({ sourceId: entry.id, pageId: entry.pages[0].id })} key={entry.id}>{entry.title}<small>{entry.pages.length} pages</small></button>)}</details>}
      </> : <p className="margin-empty">{source ? source.status === 'error' ? `${source.title}: ${source.error || 'Source ingestion failed.'}` : `Preparing ${source.title}. Page references will appear when extraction finishes.` : 'Imported sources and their page references appear here.'}</p>}
      <div className="margin-ask"><h2><IconMessageCircle size={21} aria-hidden="true" /> Ask the tutor</h2><p>{mode === 'lessons' ? 'Use “Ask about this moment” below the lesson to attach its scene and timestamp.' : 'Ask about your course or attach a source region.'}</p><button className="button primary compact" type="button" onClick={() => onTab('tutor')}>Open tutor</button></div>
    </section>
    <div className="margin-tutor" hidden={tab !== 'tutor'}>{children}</div>
    <section className="notes-margin-content" aria-label="Course flashcards" hidden={tab !== 'flashcards'}>
      {cards.length ? cards.map((card) => <MarginFlashcard item={card} key={card.id} />) : <p className="margin-empty">No flashcards in this course yet.</p>}
      <button className="button compact" type="button" onClick={onOpenStudy}>Manage flashcards</button>
    </section>
  </>
}

function CourseSources({ sources, onCitation }: { sources: Source[]; onCitation: (target: CitationTarget) => void }) {
  return <div className="margin-course-sources">{sources.length ? sources.map((source) => <button type="button" key={source.id} disabled={!source.pages.length} onClick={() => onCitation({ sourceId: source.id, pageId: source.pages[0].id })}>
    <span>{source.title}</span><small>{source.status === 'error' ? 'Extraction failed' : source.pages.length ? `${source.pages.length} pages` : 'Preparing source'}</small>
  </button>) : <p className="margin-empty">No sources in this course yet.</p>}</div>
}

function MarginFlashcard({ item }: { item: StudyItem }) {
  const [revealed, setRevealed] = useState(false)
  const answer = typeof item.data.answer === 'string' ? item.data.answer : item.body
  return <article className="margin-flashcard"><h2><MathText text={item.title} /></h2>{revealed && <p><MathText text={answer || 'No answer saved.'} /></p>}<button className="text-button" type="button" aria-expanded={revealed} onClick={() => setRevealed((value) => !value)}>{revealed ? 'Hide answer' : 'Reveal answer'}</button></article>
}

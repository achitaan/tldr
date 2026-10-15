import { useEffect, useRef, useState } from 'react'
import {
  IconArrowLeft,
  IconArrowRight,
  IconCheck,
  IconFilePlus,
  IconFocus2,
  IconPhoto,
  IconRotateClockwise,
  IconTextPlus,
  IconTrash,
  IconZoomIn,
  IconZoomOut,
} from '../icons'
import { api } from '../lib/api'
import {
  clientToNormalized,
  normalizedRect,
  rotatedSize,
  rotationTransform,
  type Point,
  type Rotation,
} from '../lib/geometry'
import type { CitationTarget, Course, Region, Source, SourcePage } from '../types'
import { ConfirmDialog } from './ConfirmDialog'
import { MathText } from './MathText'
import { readingBlocks } from '../lib/reading'

type Props = {
  active: boolean
  courseId: Course['id']
  sources: Source[]
  demo: boolean
  citationTarget?: CitationTarget
  selectedRegionIds: Region['id'][]
  navigationTarget?: { sourceId: Source['id']; pageIndex: number }
  onReadingSelection?: (target: { sourceId: Source['id']; pageId?: SourcePage['id'] }) => void
  onToggleRegion: (regionId: Region['id']) => void
  onSourcesChange: (sources: Source[]) => void
  onRefresh: () => void
  onNotice: (message: string) => void
}

const emptyRegion = { x: 0.1, y: 0.1, width: 0.3, height: 0.2 }

export function SourceWorkspace({
  active,
  courseId,
  sources,
  demo,
  citationTarget,
  selectedRegionIds,
  navigationTarget,
  onReadingSelection,
  onToggleRegion,
  onSourcesChange,
  onRefresh,
  onNotice,
}: Props) {
  const [sourceId, setSourceId] = useState<Source['id'] | undefined>(sources[0]?.id)
  const [pageIndex, setPageIndex] = useState(0)
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState<Rotation>(0)
  const [drawing, setDrawing] = useState(false)
  const [draft, setDraft] = useState(emptyRegion)
  const [activeRegionId, setActiveRegionId] = useState<Region['id'] | undefined>()
  const [text, setText] = useState('')
  const [previewMath, setPreviewMath] = useState(false)
  const [workspaceMode, setWorkspaceMode] = useState<'reading' | 'source'>('reading')
  const [saving, setSaving] = useState(false)
  const [showAdd, setShowAdd] = useState<'file' | 'text' | 'web' | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const pendingCitation = useRef<{ pageId: SourcePage['id']; regionId?: Region['id'] } | null>(null)
  const handledCitation = useRef<CitationTarget | undefined>()
  const readingScrollRef = useRef<HTMLDivElement>(null)
  const sourceToolsScrollRef = useRef<HTMLDivElement>(null)
  const savedScroll = useRef({ reading: 0, source: 0 })

  const source = sources.find((entry) => entry.id === sourceId) ?? sources[0]
  const page = source?.pages[pageIndex]
  const pageRef = useRef(page)
  pageRef.current = page
  const selectedSourceId = source?.id
  const pageId = page?.id

  useEffect(() => {
    if (!navigationTarget) return
    setSourceId(navigationTarget.sourceId)
    setPageIndex(navigationTarget.pageIndex)
  }, [navigationTarget])

  useEffect(() => {
    if (!sources.some((entry) => entry.id === sourceId)) {
      setSourceId(sources[0]?.id)
      setPageIndex(0)
    }
  }, [sourceId, sources])

  useEffect(() => {
    if (!citationTarget || handledCitation.current === citationTarget) return
    const nextSource = sources.find((entry) => entry.id === citationTarget.sourceId)
    const nextPageIndex = nextSource?.pages.findIndex((entry) => entry.id === citationTarget.pageId) ?? -1
    if (nextSource && nextPageIndex >= 0) {
      handledCitation.current = citationTarget
      pendingCitation.current = { pageId: citationTarget.pageId, regionId: citationTarget.regionId }
      setSourceId(nextSource.id)
      setPageIndex(nextPageIndex)
      setActiveRegionId(citationTarget.regionId)
      if (citationTarget.regionId !== undefined) setWorkspaceMode('source')
    }
  }, [citationTarget, sources])

  useEffect(() => {
    const currentPage = pageRef.current
    setText(currentPage?.text ?? '')
    const citation = pendingCitation.current
    if (currentPage && citation?.pageId === currentPage.id) {
      const region = currentPage.regions.find((entry) => entry.id === citation.regionId)
      setActiveRegionId(citation.regionId)
      if (region) setDraft({ x: region.x, y: region.y, width: region.width, height: region.height })
      pendingCitation.current = null
    } else {
      setActiveRegionId(undefined)
      setDraft(emptyRegion)
    }
  }, [pageId])

  useEffect(() => {
    if (selectedSourceId !== undefined) onReadingSelection?.({ sourceId: selectedSourceId, pageId })
  }, [selectedSourceId, pageId, onReadingSelection])

  useEffect(() => {
    if (!active) {
      savedScroll.current.reading = readingScrollRef.current?.scrollTop ?? savedScroll.current.reading
      savedScroll.current.source = sourceToolsScrollRef.current?.scrollTop ?? savedScroll.current.source
      return
    }
    const frame = window.requestAnimationFrame(() => {
      if (readingScrollRef.current) readingScrollRef.current.scrollTop = savedScroll.current.reading
      if (sourceToolsScrollRef.current) sourceToolsScrollRef.current.scrollTop = savedScroll.current.source
    })
    return () => window.cancelAnimationFrame(frame)
  }, [active])

  const deleteSource = async () => {
    if (!source) return
    if (demo) {
      onNotice('Demo sources are curated and cannot be removed.')
      setConfirmDelete(false)
      return
    }
    setDeleting(true)
    try {
      await api.deleteSource(source.id)
      const remaining = sources.filter((entry) => entry.id !== source.id)
      onSourcesChange(remaining)
      setSourceId(remaining[0]?.id)
      setPageIndex(0)
      setConfirmDelete(false)
      onNotice(`Removed ${source.title} from this course.`)
      onRefresh()
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Source could not be removed.')
    } finally {
      setDeleting(false)
    }
  }

  const replacePage = (nextPage: SourcePage) => {
    onSourcesChange(sources.map((entry) => entry.id === source?.id
      ? { ...entry, pages: entry.pages.map((candidate) => candidate.id === nextPage.id ? nextPage : candidate) }
      : entry))
  }

  const saveText = async () => {
    if (!page || text === page.text) return
    setSaving(true)
    try {
      if (demo) replacePage({ ...page, text, corrected: true })
      else replacePage(await api.updatePage(page.id, text))
      onNotice('Page text saved and queued for retrieval reindexing.')
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Page text could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  const saveRegion = async () => {
    if (!page) return
    setSaving(true)
    const active = page.regions.find((region) => region.id === activeRegionId)
    try {
      const nextRegion = active
        ? demo
          ? { ...active, ...draft }
          : await api.updateRegion(active.id, draft)
        : demo
          ? { id: `demo-region-${Date.now()}`, page: page.id, label: 'Study region', ...draft, confirmed: true }
          : await api.createRegion({ page: page.id, label: 'Study region', ...draft, confirmed: true })
      replacePage({
        ...page,
        regions: active
          ? page.regions.map((region) => region.id === active.id ? nextRegion : region)
          : [...page.regions, nextRegion],
      })
      setActiveRegionId(nextRegion.id)
      setDrawing(false)
      onNotice(active ? 'Region coordinates updated.' : 'Region saved to this page.')
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Region could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  if (!source || !page) {
    return (
      <section className="source-workspace" aria-label="Source workspace" data-active={active}>
        <div className="empty-state notes-source-empty" aria-labelledby="empty-source-title">
          <IconPhoto size={34} aria-hidden="true" />
          <h2 id="empty-source-title">{source ? source.status === 'error' ? 'Source ingestion failed' : `Preparing ${source.title}` : 'Bring in a source'}</h2>
          <p>{source ? source.error || 'The source is queued for extraction. Pages and editable text will appear here when ingestion completes.' : 'Add a PDF, image, or text note. Extracted text and page visuals stay together.'}</p>
          <div className="button-row">
            <button className={source ? 'button' : 'button primary'} type="button" onClick={() => setShowAdd('file')}>
              <IconFilePlus size={18} aria-hidden="true" /> Upload source
            </button>
            <button className="button" type="button" onClick={() => setShowAdd('text')}>
              <IconTextPlus size={18} aria-hidden="true" /> Paste text
            </button>
            {source && <button className="button danger-ghost" type="button" onClick={() => setConfirmDelete(true)}><IconTrash size={18} aria-hidden="true" /> Remove source</button>}
            <button className="button" type="button" onClick={() => setShowAdd('web')}>Import webpage</button>
          </div>
          {showAdd && <AddSource mode={showAdd} courseId={courseId} demo={demo} onClose={() => setShowAdd(null)} onAdded={(next) => { onSourcesChange([...sources, next]); setSourceId(next.id); onRefresh() }} onNotice={onNotice} />}
          {confirmDelete && source && <ConfirmDialog title={`Remove ${source.title}?`} message="This removes the queued source and any extracted content. This cannot be undone." confirmLabel="Remove source" busy={deleting} onCancel={() => setConfirmDelete(false)} onConfirm={() => void deleteSource()} />}
        </div>
      </section>
    )
  }

  return (
    <section className="source-workspace" aria-label="Source workspace" data-active={active}>
      <header className="workspace-header">
        <div>
          <span className="quiet-label">Source desk</span>
          <h1>{source.title}</h1>
          {source.kind === 'web' && <p><span className="status-tag">Web text extraction</span> <a href={source.fetched_url || source.source_url} target="_blank" rel="noopener noreferrer">Open original page</a></p>}
        </div>
        <div className="button-row source-header-actions">
          <div className="source-mode-switch" aria-label="Notes view">
            <button className={workspaceMode === 'reading' ? 'segmented active' : 'segmented'} type="button" aria-pressed={workspaceMode === 'reading'} onClick={() => setWorkspaceMode('reading')}>Read</button>
            <button className={workspaceMode === 'source' ? 'segmented active' : 'segmented'} type="button" aria-pressed={workspaceMode === 'source'} onClick={() => setWorkspaceMode('source')}>Source tools</button>
          </div>
          <details className="source-actions-menu"><summary className="button compact">Source actions</summary><div>
            <button className="button compact" type="button" onClick={() => setShowAdd('file')}><IconFilePlus size={17} aria-hidden="true" /> Add source</button>
            <button className="button compact" type="button" onClick={() => setShowAdd('text')}><IconTextPlus size={17} aria-hidden="true" /> Paste text</button>
            <button className="button compact" type="button" onClick={() => setShowAdd('web')}>Import webpage</button>
            <button className="button compact danger-ghost" type="button" onClick={() => setConfirmDelete(true)}><IconTrash size={17} aria-hidden="true" /> Remove</button>
          </div></details>
        </div>
      </header>

      {workspaceMode === 'reading' ? (
        <div className={page.regions.length > 0 ? 'reading-page-shell has-regions' : 'reading-page-shell'} ref={readingScrollRef}>
          <div className="reader-toolbar">
            <div className="page-stepper" aria-label="Reading pages">
              <button className="icon-button" type="button" aria-label="Previous page" disabled={pageIndex === 0} onClick={() => setPageIndex((value) => value - 1)}><IconArrowLeft size={18} /></button>
              <span>Page {pageIndex + 1} of {source.pages.length}</span>
              <button className="icon-button" type="button" aria-label="Next page" disabled={pageIndex >= source.pages.length - 1} onClick={() => setPageIndex((value) => value + 1)}><IconArrowRight size={18} /></button>
            </div>
            <span className="reader-source-label">{source.kind === 'web' ? 'Web extraction' : 'Source text'}</span>
          </div>
          <article className="reading-page" aria-label={`${source.title}, page ${page.number}`}>
            <span className="quiet-label">{source.title} · {page.number}</span>
            <div className="reading-copy"><ReadingContent text={text} /></div>
            {text !== page.text && <p className="reader-unsaved" role="status">This page has an unsaved text correction. Open Source tools to review or save it.</p>}
          </article>
          {page.regions.length > 0 && <aside className="reading-regions" aria-label="Page source regions"><h3>Source margin</h3>{page.regions.map((region, index) => <button type="button" className={selectedRegionIds.includes(region.id) ? 'region-row selected' : 'region-row'} onClick={() => onToggleRegion(region.id)} key={region.id}><span className="region-number">{index + 1}</span><span><strong>{region.label || `Region ${index + 1}`}</strong><small>{region.text || 'No region text yet'}</small></span><span>{selectedRegionIds.includes(region.id) ? 'In chat' : 'Add'}</span></button>)}</aside>}
        </div>
      ) : <div className="source-columns" ref={sourceToolsScrollRef}>
        <div className="viewer-column">
          {source.kind === 'web' ? <div className="region-editor"><div>
            <div className="page-stepper" aria-label="Web extraction pages">
              <button className="icon-button" type="button" aria-label="Previous extraction page" disabled={pageIndex === 0} onClick={() => setPageIndex((value) => value - 1)}><IconArrowLeft size={18} /></button>
              <span>Part {pageIndex + 1} of {source.pages.length}</span>
              <button className="icon-button" type="button" aria-label="Next extraction page" disabled={pageIndex >= source.pages.length - 1} onClick={() => setPageIndex((value) => value + 1)}><IconArrowRight size={18} /></button>
            </div>
            <strong>Extracted webpage text</strong><p>{source.extraction_notes}</p><p>{source.fetched_at && `Fetched ${new Date(source.fetched_at).toLocaleString()}`}</p><p><a href={source.fetched_url || source.source_url} target="_blank" rel="noopener noreferrer">View original equations and diagrams</a>{source.original_url && <> · <a href={source.original_url} download>Download saved HTML</a></>}</p><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{page.original_text || page.text}</pre>
          </div></div> : <>
          <div className="viewer-toolbar" aria-label="Page controls">
            <div className="page-stepper">
              <button className="icon-button" type="button" aria-label="Previous page" disabled={pageIndex === 0} onClick={() => setPageIndex((value) => value - 1)}><IconArrowLeft size={18} /></button>
              <span>Page {pageIndex + 1} of {source.pages.length}</span>
              <button className="icon-button" type="button" aria-label="Next page" disabled={pageIndex >= source.pages.length - 1} onClick={() => setPageIndex((value) => value + 1)}><IconArrowRight size={18} /></button>
            </div>
            <div className="button-row">
              <button className="icon-button" type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.6, value - 0.2))}><IconZoomOut size={18} /></button>
              <span className="zoom-readout">{Math.round(zoom * 100)}%</span>
              <button className="icon-button" type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(2.4, value + 0.2))}><IconZoomIn size={18} /></button>
              <button className="icon-button" type="button" aria-label={`Rotate page, currently ${rotation} degrees`} onClick={() => setRotation(((rotation + 90) % 360) as Rotation)}><IconRotateClockwise size={18} /></button>
              <button className={drawing ? 'button compact active' : 'button compact'} type="button" aria-pressed={drawing} onClick={() => setDrawing((value) => !value)}><IconFocus2 size={17} aria-hidden="true" /> Mark region</button>
            </div>
          </div>

          <PageCanvas
            page={page}
            zoom={zoom}
            rotation={rotation}
            drawing={drawing}
            draft={draft}
            activeRegionId={activeRegionId}
            selectedRegionIds={selectedRegionIds}
            onDraft={setDraft}
            onRegion={(region) => {
              setActiveRegionId(region.id)
              setDraft({ x: region.x, y: region.y, width: region.width, height: region.height })
            }}
            onToggleRegion={onToggleRegion}
          />

          <div className="region-editor">
            <div>
              <strong>{activeRegionId ? 'Adjust selected region' : 'Region coordinates'}</strong>
              <p>Draw on the page or enter normalized values from 0 to 1.</p>
            </div>
            <div className="coordinate-grid">
              {(['x', 'y', 'width', 'height'] as const).map((field) => (
                <label key={field}>{field}
                  <input type="number" min="0" max="1" step="0.01" value={Number(draft[field].toFixed(2))} onChange={(event) => setDraft({ ...draft, [field]: Number(event.target.value) })} />
                </label>
              ))}
              <button className="button primary compact" type="button" disabled={saving || draft.width <= 0 || draft.height <= 0 || draft.x + draft.width > 1 || draft.y + draft.height > 1} onClick={saveRegion}>
                <IconCheck size={17} aria-hidden="true" /> {saving ? 'Saving' : 'Save region'}
              </button>
            </div>
          </div>
          </>}
        </div>

        <aside className="text-column" aria-labelledby="extracted-text-heading">
          <div className="text-editor-heading">
            <div>
              <span className="quiet-label">Editable extraction</span>
              <h2 id="extracted-text-heading">Page text</h2>
            </div>
            {page.corrected && <span className="status-tag">Corrected</span>}
            <button className="text-button" type="button" aria-pressed={previewMath} onClick={() => setPreviewMath((value) => !value)}>{previewMath ? 'Edit text' : 'Preview math'}</button>
          </div>
          {!previewMath && <label className="sr-only" htmlFor="page-text">Extracted page text</label>}
          {previewMath ? <div className="math-source-preview" role="region" aria-label="Formatted page text"><MathText text={text} /></div> : <textarea id="page-text" value={text} onChange={(event) => setText(event.target.value)} spellCheck="true" />}
          <div className="text-editor-footer">
            <span>{text.length.toLocaleString()} characters</span>
            <button className="button primary compact" type="button" disabled={saving || text === page.text} onClick={saveText}>{saving ? 'Saving' : 'Save correction'}</button>
          </div>
          {page.regions.length > 0 && (
            <div className="region-list">
              <h3>Page regions</h3>
              {page.regions.map((region, index) => (
                <button
                  type="button"
                  className={selectedRegionIds.includes(region.id) ? 'region-row selected' : 'region-row'}
                  onClick={() => onToggleRegion(region.id)}
                  key={region.id}
                >
                  <span className="region-number">{index + 1}</span>
                  <span><strong>{region.label || `Region ${index + 1}`}</strong><small>{region.text || 'No region text yet'}</small></span>
                  <span>{selectedRegionIds.includes(region.id) ? 'In chat' : 'Add'}</span>
                </button>
              ))}
            </div>
          )}
        </aside>
      </div>}
      {showAdd && <AddSource mode={showAdd} courseId={courseId} demo={demo} onClose={() => setShowAdd(null)} onAdded={(next) => { onSourcesChange([...sources, next]); setSourceId(next.id); onRefresh() }} onNotice={onNotice} />}
      {confirmDelete && <ConfirmDialog title={`Remove ${source.title}?`} message="This removes the source, its page images, extracted text, and regions from this course. Existing lesson videos may retain copies; delete the course to remove its lessons and render cache. This cannot be undone." confirmLabel="Remove source" busy={deleting} onCancel={() => setConfirmDelete(false)} onConfirm={() => void deleteSource()} />}
    </section>
  )
}

function ReadingContent({ text }: { text: string }) {
  const blocks = readingBlocks(text)
  return <>{blocks.flatMap((block, index) => {
    const heading = block.match(/^#{1,6}\s+([^\n]+)(?:\n([\s\S]+))?$/)
    if (!heading) return <p key={`body-${index}`}><MathText text={block.trim()} /></p>
    const items = [<h2 className="source-text-heading" key={`heading-${index}`}><MathText text={heading[1].trim()} /></h2>]
    if (heading[2]?.trim()) items.push(<p key={`heading-body-${index}`}><MathText text={heading[2].trim()} /></p>)
    return items
  })}</>
}

type CanvasProps = {
  page: SourcePage
  zoom: number
  rotation: Rotation
  drawing: boolean
  draft: typeof emptyRegion
  activeRegionId?: Region['id']
  selectedRegionIds: Region['id'][]
  onDraft: (rect: typeof emptyRegion) => void
  onRegion: (region: Region) => void
  onToggleRegion: (regionId: Region['id']) => void
}

function PageCanvas({ page, zoom, rotation, drawing, draft, activeRegionId, selectedRegionIds, onDraft, onRegion, onToggleRegion }: CanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [dragStart, setDragStart] = useState<Point | null>(null)
  const sourceWidth = page.width || 1000
  const sourceHeight = page.height || 1400
  const size = rotatedSize(sourceWidth, sourceHeight, rotation)
  const transform = rotationTransform(sourceWidth, sourceHeight, rotation)

  const pointFromEvent = (event: React.PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    return clientToNormalized({ x: event.clientX, y: event.clientY }, rect, sourceWidth, sourceHeight, rotation)
  }

  return (
    <div className={drawing ? 'page-viewport drawing' : 'page-viewport'}>
      <svg
        ref={svgRef}
        className="page-canvas"
        style={{ width: `${Math.max(zoom * 100, 60)}%` }}
        viewBox={`0 0 ${size.width} ${size.height}`}
        role="img"
        aria-label={`Page ${page.number} visual with ${page.regions.length} marked regions`}
        onPointerDown={(event) => {
          if (!drawing) return
          event.currentTarget.setPointerCapture(event.pointerId)
          const start = pointFromEvent(event)
          setDragStart(start)
          onDraft({ x: start.x, y: start.y, width: 0, height: 0 })
        }}
        onPointerMove={(event) => {
          if (!drawing || !dragStart) return
          onDraft(normalizedRect(dragStart, pointFromEvent(event)))
        }}
        onPointerUp={(event) => {
          if (!drawing || !dragStart) return
          onDraft(normalizedRect(dragStart, pointFromEvent(event)))
          setDragStart(null)
        }}
      >
        <g transform={transform}>
          <rect width={sourceWidth} height={sourceHeight} fill="#fffdf7" />
          {page.image_url
            ? <image href={page.image_url} width={sourceWidth} height={sourceHeight} preserveAspectRatio="xMidYMid meet" />
            : page.demo_kind
              ? <DemoDiagram kind={page.demo_kind} width={sourceWidth} height={sourceHeight} />
              : <TextPageDiagram text={page.text} width={sourceWidth} height={sourceHeight} />}
          {page.regions.map((region, index) => (
            <g key={region.id} className="region-mark" role="button" aria-label={`${region.label || `Region ${index + 1}`}${selectedRegionIds.includes(region.id) ? ', added to chat' : ''}`} tabIndex={0} onClick={(event) => { event.stopPropagation(); onRegion(region) }} onDoubleClick={() => onToggleRegion(region.id)} onKeyDown={(event) => { if (event.key === 'Enter') onToggleRegion(region.id) }}>
              <rect
                x={region.x * sourceWidth}
                y={region.y * sourceHeight}
                width={region.width * sourceWidth}
                height={region.height * sourceHeight}
                className={`${activeRegionId === region.id ? 'active ' : ''}${selectedRegionIds.includes(region.id) ? 'selected' : ''}`}
              />
              <text x={region.x * sourceWidth + 12} y={region.y * sourceHeight + 25}>{index + 1}</text>
            </g>
          ))}
          {drawing && draft.width > 0 && draft.height > 0 && (
            <rect className="draft-region" x={draft.x * sourceWidth} y={draft.y * sourceHeight} width={draft.width * sourceWidth} height={draft.height * sourceHeight} />
          )}
        </g>
      </svg>
    </div>
  )
}

function TextPageDiagram({ text, width, height }: { text: string; width: number; height: number }) {
  const words = text.split(/\s+/)
  const lines: string[] = []
  for (const word of words) {
    const last = lines[lines.length - 1]
    if (!last || `${last} ${word}`.length > 72) lines.push(word)
    else lines[lines.length - 1] = `${last} ${word}`
    if (lines.length >= 22) break
  }
  return <g><text x={width * .1} y={height * .1} className="diagram-title">Text source</text>{lines.map((line, index) => <text x={width * .1} y={height * .16 + index * 44} className="text-page-line" key={`${index}-${line}`}>{line}</text>)}</g>
}

function DemoDiagram({ kind, width, height }: { kind?: SourcePage['demo_kind']; width: number; height: number }) {
  if (kind === 'bus') return (
    <g className="diagram bus-diagram">
      <rect x="80" y="92" width="1040" height="615" rx="18" fill="#f8f2e7" stroke="#d9cfbd" strokeWidth="3" />
      <text x="130" y="162" className="diagram-title">Simplified read handshake</text>
      <rect x="130" y="225" width="190" height="105" rx="12" fill="#2a7770" />
      <rect x="880" y="225" width="190" height="105" rx="12" fill="#d9663d" />
      <text x="174" y="288" fill="#fff" fontSize="30" fontWeight="700">Processor</text>
      <text x="927" y="288" fill="#fff" fontSize="30" fontWeight="700">Memory</text>
      <line x1="340" y1="250" x2="860" y2="250" stroke="#2a4d49" strokeWidth="8" />
      <polygon points="860,250 830,234 830,266" fill="#2a4d49" />
      <text x="485" y="230" className="diagram-label">address 16 + read</text>
      <line x1="860" y1="310" x2="340" y2="310" stroke="#d9663d" strokeWidth="8" />
      <polygon points="340,310 370,294 370,326" fill="#d9663d" />
      <text x="510" y="355" className="diagram-label">data 42 + valid</text>
      <line x1="150" y1="480" x2="1035" y2="480" stroke="#2a4d49" strokeWidth="3" />
      {[240, 410, 610, 800, 970].map((x) => <line key={x} x1={x} y1="462" x2={x} y2="498" stroke="#2a4d49" strokeWidth="4" />)}
      <polyline points="150,580 410,580 410,525 800,525 800,580 1035,580" fill="none" stroke="#2a7770" strokeWidth="8" />
      <polyline points="150,650 610,650 610,610 800,610 800,650 1035,650" fill="none" stroke="#d9663d" strokeWidth="8" />
      <text x="155" y="550" className="diagram-note">read request</text>
      <text x="155" y="625" className="diagram-note">data valid</text>
      <text x="625" y="445" className="diagram-label">safe sample window</text>
    </g>
  )
  if (kind === 'math') return (
    <g className="diagram math-diagram">
      <text x="105" y="125" className="diagram-title">Distance over time</text>
      <line x1="160" y1="650" x2="1040" y2="650" stroke="#223c39" strokeWidth="4" />
      <line x1="160" y1="650" x2="160" y2="150" stroke="#223c39" strokeWidth="4" />
      <polyline points="160,620 310,570 430,490 555,330 700,265 850,245 1000,170" fill="none" stroke="#2a7770" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="425" y1="535" x2="680" y2="210" stroke="#d9663d" strokeWidth="5" strokeDasharray="15 11" />
      <text x="665" y="198" className="diagram-label">tangent</text>
      <text x="955" y="705" className="diagram-note">time</text>
      <text x="68" y="170" className="diagram-note" transform="rotate(-90 68 170)">distance</text>
    </g>
  )
  if (kind === 'finance') return (
    <g className="diagram finance-diagram">
      <text x="105" y="125" className="diagram-title">Compounding changes the base</text>
      <line x1="155" y1="650" x2="1040" y2="650" stroke="#223c39" strokeWidth="4" />
      <line x1="155" y1="650" x2="155" y2="155" stroke="#223c39" strokeWidth="4" />
      {[0, 1, 2, 3, 4, 5].map((n) => <g key={n}><rect x={220 + n * 135} y={570 - n * n * 14} width="72" height={80 + n * n * 14} fill={n < 3 ? '#87aaa5' : '#2a7770'} /><text x={246 + n * 135} y="690" className="diagram-note">{n}</text></g>)}
      <polyline points="256,570 391,545 526,485 661,390 796,260 931,105" fill="none" stroke="#d9663d" strokeWidth="7" />
      <text x="710" y="185" className="diagram-label">growth on prior growth</text>
    </g>
  )
  if (kind === 'biology') return (
    <g className="diagram biology-diagram">
      <text x="105" y="125" className="diagram-title">Signal across a cell membrane</text>
      <rect x="90" y="310" width="1020" height="88" rx="44" fill="#e7d7b9" />
      {Array.from({ length: 16 }, (_, index) => <circle key={index} cx={125 + index * 64} cy={335 + (index % 2) * 36} r="18" fill="#c69059" />)}
      <path d="M520 245 C470 290 480 430 535 474 C590 430 600 290 550 245 Z" fill="#2a7770" />
      <circle cx="535" cy="205" r="42" fill="#d9663d" />
      <line x1="535" y1="485" x2="535" y2="595" stroke="#d9663d" strokeWidth="8" strokeDasharray="12 12" />
      <circle cx="535" cy="620" r="28" fill="#f0b76c" />
      <circle cx="700" cy="620" r="28" fill="#f0b76c" />
      <circle cx="865" cy="620" r="28" fill="#f0b76c" />
      <line x1="570" y1="620" x2="665" y2="620" stroke="#2a7770" strokeWidth="5" />
      <line x1="735" y1="620" x2="830" y2="620" stroke="#2a7770" strokeWidth="5" />
      <text x="622" y="555" className="diagram-label">intracellular relay</text>
    </g>
  )
  return <g><text x={width / 2} y={height / 2} textAnchor="middle" className="diagram-note">Page image unavailable</text></g>
}

function AddSource({ mode, courseId, demo, onClose, onAdded, onNotice }: {
  mode: 'file' | 'text' | 'web'
  courseId: Course['id']
  demo: boolean
  onClose: () => void
  onAdded: (source: Source) => void
  onNotice: (message: string) => void
}) {
  const [title, setTitle] = useState('')
  const [textValue, setTextValue] = useState('')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const valid = mode === 'file' ? Boolean(file) : mode === 'web' ? url.startsWith('https://') : title.trim().length > 0 && textValue.trim().length > 0

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!valid) return
    if (demo) {
      onNotice('Demo mode is read-only. Open the local app to import your own sources.')
      onClose()
      return
    }
    setBusy(true)
    try {
      const source = mode === 'file' && file
        ? await api.uploadSource(courseId, file)
        : mode === 'web' ? await api.createWebSource(courseId, url.trim(), title)
        : await api.createTextSource(courseId, title, textValue)
      onAdded(source)
      onNotice('Source added. Ingestion continues in the activity queue.')
      onClose()
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Source could not be added.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="add-source-title">
        <header><div><span className="quiet-label">Course source</span><h2 id="add-source-title">{mode === 'file' ? 'Upload a document' : mode === 'web' ? 'Import a webpage' : 'Add a text note'}</h2></div><button className="button compact" type="button" onClick={onClose}>Close</button></header>
        <form onSubmit={submit}>
          {mode === 'file' ? (
            <label className="file-drop">Choose a PDF, image, text, or Markdown file
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.md" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
              <small>{file ? `${file.name} (${Math.ceil(file.size / 1024)} KB)` : 'Maximum 20 MB. PDFs may contain up to 100 pages.'}</small>
            </label>
          ) : mode === 'web' ? (
            <>
              <label>Webpage URL<input type="url" required maxLength={2048} placeholder="https://tutorial.math.lamar.edu/Classes/CalcI/DerivativeIntro.aspx" value={url} onChange={(event) => setUrl(event.target.value)} /></label>
              <label>Title (optional)<input maxLength={240} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
              <p className="inline-note">Imports one public HTTPS page. Source TeX and image descriptions are retained when available. Images, interactive content, and scripts are not imported. Use the original page or upload a PDF for diagrams.</p>
            </>
          ) : (
            <>
              <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
              <label>Text<textarea value={textValue} onChange={(event) => setTextValue(event.target.value)} rows={10} /></label>
            </>
          )}
          {demo && <p className="inline-note">This public demo never uploads files or calls the API.</p>}
          <div className="button-row end"><button className="button primary" type="submit" disabled={!valid || busy}>{busy ? 'Adding source' : demo ? 'Close demo notice' : 'Add source'}</button></div>
        </form>
      </section>
    </div>
  )
}

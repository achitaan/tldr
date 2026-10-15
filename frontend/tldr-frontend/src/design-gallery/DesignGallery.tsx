import { useEffect, useMemo, useRef, useState } from 'react'
import {
  IconArrowLeft,
  IconArrowRight,
  IconBook2,
  IconCheck,
  IconLayoutSidebarLeftCollapse,
  IconMessageCircle,
  IconPhoto,
  IconPlayerPlay,
  IconRefresh,
  IconSparkles,
  IconX,
} from '../icons'
import './design-gallery.css'

type Direction = {
  id: string
  number: string
  name: string
  premise: string
  bestFor: string
  tone: string
}

const directions: Direction[] = [
  { id: 'focus-canvas', number: '01', name: 'Focus Canvas', premise: 'A calm split between the original source and the active explanation.', bestFor: 'Deep study', tone: 'Quiet / precise' },
  { id: 'evidence-desk', number: '02', name: 'Evidence Desk', premise: 'A research console that keeps every claim visibly attached to evidence.', bestFor: 'Source-heavy courses', tone: 'Dense / rigorous' },
  { id: 'lecture-atlas', number: '03', name: 'Lecture Atlas', premise: 'A navigable lesson map with the current concept as the visual center.', bestFor: 'Long lectures', tone: 'Spatial / guided' },
  { id: 'study-ledger', number: '04', name: 'Study Ledger', premise: 'A structured academic notebook with marginal citations and recall checks.', bestFor: 'Review sessions', tone: 'Editorial / ordered' },
  { id: 'signal-lab', number: '05', name: 'Signal Lab', premise: 'A compact instrumentation view for technical material and fast iteration.', bestFor: 'Engineering labs', tone: 'Technical / active' },
  { id: 'quiet-tutor', number: '06', name: 'Quiet Tutor', premise: 'One question and one explanation at a time, with supporting evidence nearby.', bestFor: 'Focused tutoring', tone: 'Warm / minimal' },
  { id: 'blackboard', number: '07', name: 'Blackboard Session', premise: 'A dark teaching surface that treats annotations as the primary interaction.', bestFor: 'Live walkthroughs', tone: 'Tactile / direct' },
  { id: 'blueprint', number: '08', name: 'Blueprint Grid', premise: 'A measured technical drawing language for diagrams, variables, and proof steps.', bestFor: 'Circuit analysis', tone: 'Engineered / exact' },
  { id: 'recall-sprint', number: '09', name: 'Recall Sprint', premise: 'A retrieval-first layout that turns each lesson beat into a testable prompt.', bestFor: 'Exam preparation', tone: 'Fast / motivating' },
  { id: 'source-first', number: '10', name: 'Source First', premise: 'The uploaded page stays dominant while tutor and lesson tools orbit it.', bestFor: 'Diagram fidelity', tone: 'Visual / trustworthy' },
]

const lessonSteps = [
  { time: '0:00', title: 'Request', body: 'The processor places an address on the address bus and asks memory for a value.' },
  { time: '0:28', title: 'Decode', body: 'The address decoder selects one memory location. Only that location responds.' },
  { time: '0:54', title: 'Return', body: 'The selected value travels back on the data bus and is captured by the processor.' },
]

export default function DesignGallery() {
  const [selected, setSelected] = useState(0)
  const [compareWith, setCompareWith] = useState(7)
  const [compare, setCompare] = useState(false)
  const previewRef = useRef<HTMLElement>(null)

  const selectDirection = (index: number) => {
    setSelected(index)
    requestAnimationFrame(() => previewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return
      if (event.key === '[') setSelected((value) => (value + directions.length - 1) % directions.length)
      if (event.key === ']') setSelected((value) => (value + 1) % directions.length)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const current = directions[selected]
  const secondary = directions[compareWith]

  return (
    <div className="dg-shell">
      <a className="dg-skip" href="#design-preview">Skip to selected design</a>
      <header className="dg-intro">
        <a className="dg-back" href="/"><IconArrowLeft size={18} aria-hidden="true" /> Return to TLDR</a>
        <div className="dg-intro-grid">
          <div>
            <p className="dg-kicker">TLDR workspace study · 10 directions</p>
            <h1>Same lesson.<br />Ten ways to learn it.</h1>
          </div>
          <div className="dg-brief">
            <p>Every direction uses the same processor-memory teaching sample, source frame, citation, tutor response, playback state, and recall prompt.</p>
            <div className="dg-guardrail"><IconPhoto size={20} aria-hidden="true" /><span><strong>Source fidelity rule</strong>Uploaded screenshots and PDF diagrams stay original. Highlights are overlays. Any generated technical drawing is labelled conceptual.</span></div>
          </div>
        </div>
      </header>

      <main>
        <section className="dg-overview" aria-labelledby="directions-title">
          <div className="dg-section-title">
            <div><p className="dg-kicker">Overview</p><h2 id="directions-title">Choose a direction</h2></div>
            <p>Open any concept at full size. Use compare mode to test two organizing ideas side by side.</p>
          </div>
          <div className="dg-card-grid">
            {directions.map((direction, index) => (
              <button
                className={`dg-direction-card dg-card-${direction.id}${selected === index ? ' is-selected' : ''}`}
                type="button"
                aria-pressed={selected === index}
                onClick={() => selectDirection(index)}
                key={direction.id}
              >
                <span className="dg-card-top"><span>{direction.number}</span><span>{direction.tone}</span></span>
                <span className="dg-miniature" aria-hidden="true"><i /><i /><i /><i /></span>
                <strong>{direction.name}</strong>
                <span>{direction.premise}</span>
                <small>Best for {direction.bestFor.toLowerCase()}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="dg-preview-section" id="design-preview" ref={previewRef} aria-labelledby="preview-title" tabIndex={-1}>
          <div className="dg-preview-toolbar">
            <div>
              <p className="dg-kicker">Full-size preview · {current.number} of 10</p>
              <h2 id="preview-title">{current.name}</h2>
              <p>{current.premise}</p>
            </div>
            <div className="dg-toolbar-actions">
              <div className="dg-stepper" aria-label="Select design">
                <button type="button" aria-label="Previous design" onClick={() => setSelected((selected + 9) % 10)}><IconArrowLeft size={18} /></button>
                <span aria-live="polite">{current.number}</span>
                <button type="button" aria-label="Next design" onClick={() => setSelected((selected + 1) % 10)}><IconArrowRight size={18} /></button>
              </div>
              <button className={`dg-compare-toggle${compare ? ' active' : ''}`} type="button" aria-pressed={compare} onClick={() => setCompare((value) => !value)}><IconLayoutSidebarLeftCollapse size={18} aria-hidden="true" /> {compare ? 'Close comparison' : 'Compare two'}</button>
            </div>
          </div>

          {compare && (
            <div className="dg-compare-bar">
              <label htmlFor="compare-direction">Compare {current.name} with</label>
              <select id="compare-direction" value={compareWith} onChange={(event) => setCompareWith(Number(event.target.value))}>
                {directions.map((direction, index) => <option value={index} disabled={index === selected} key={direction.id}>{direction.number} · {direction.name}</option>)}
              </select>
              <p><kbd>[</kbd> and <kbd>]</kbd> move through the primary designs.</p>
            </div>
          )}

          <div className={`dg-preview-grid${compare ? ' is-comparing' : ''}`}>
            <DesignWorkspace direction={current} />
            {compare && <DesignWorkspace direction={secondary} compact />}
          </div>
        </section>
      </main>
      <footer className="dg-footer"><span>TLDR design study</span><span>Static concept interactions · no generation or API calls</span></footer>
    </div>
  )
}

function DesignWorkspace({ direction, compact = false }: { direction: Direction; compact?: boolean }) {
  const [step, setStep] = useState(0)
  const [citation, setCitation] = useState(false)
  const [recalled, setRecalled] = useState(false)
  const currentStep = lessonSteps[step]
  const progress = useMemo(() => `${Math.round(((step + 1) / lessonSteps.length) * 100)}%`, [step])

  return (
    <article className={`study-workspace sw-${direction.id}${compact ? ' is-compact' : ''}`} aria-label={`${direction.name} interactive concept`}>
      <header className="sw-topbar">
        <div className="sw-brand"><span className="sw-mark">tl;dr</span><span>TLDR teaching sample · Simulated course</span></div>
        <nav aria-label="Workspace sections"><button type="button" className="active">Study</button><button type="button">Sources</button><button type="button">Recall</button></nav>
        <span className="sw-save"><IconCheck size={15} aria-hidden="true" /> Saved</span>
      </header>

      <section className="sw-heading">
        <div><span className="sw-eyebrow">Simulated lesson 04 · Memory read cycle</span><h3>How the processor asks for a value</h3></div>
        <div className="sw-progress" aria-label={`${progress} complete`}><span style={{ width: progress }} /><small>{step + 1} / 3</small></div>
      </section>

      <section className="sw-source" aria-labelledby={`${direction.id}-source-title`}>
        <div className="sw-panel-head"><div><span>Sample source</span><strong id={`${direction.id}-source-title`}>TLDR teaching sample · 0:08</strong></div><button type="button" onClick={() => setCitation((value) => !value)} aria-expanded={citation}>Source details</button></div>
        <div className="sw-original">
          <a className="sw-source-raster" href="/sample/source-bus-frame.png" target="_blank" rel="noreferrer" aria-label="Open the unmodified TLDR sample image at full size">
            <img src="/sample/source-bus-frame.png" alt="Unmodified frame from TLDR's original processor and memory teaching animation" />
            <span className="sw-highlight" aria-hidden="true" />
          </a>
          <span className="sw-original-badge">TLDR sample · unchanged</span>
          <span className="sw-concept-badge">Highlight overlay</span>
        </div>
        {citation && <div className="sw-source-note" role="status"><IconPhoto size={17} aria-hidden="true" /><span><strong>Built-in TLDR teaching sample</strong>Original pixels and aspect ratio are preserved. The processor highlight is a separate overlay. Open the image to inspect it at full size.</span><button type="button" aria-label="Close source details" onClick={() => setCitation(false)}><IconX size={16} /></button></div>}
      </section>

      <section className="sw-lesson" aria-labelledby={`${direction.id}-lesson-title`}>
        <div className="sw-panel-head"><div><span>Lesson playback</span><strong id={`${direction.id}-lesson-title`}>{currentStep.title}</strong></div><span>{currentStep.time} / 1:18</span></div>
        <div className="sw-lesson-body">
          <button className="sw-play" type="button" aria-label="Preview next lesson step (simulated)" onClick={() => setStep((value) => (value + 1) % lessonSteps.length)}><IconPlayerPlay size={22} fill="currentColor" /></button>
          <p>{currentStep.body}</p>
        </div>
        <div className="sw-timeline" role="group" aria-label="Lesson chapters">
          {lessonSteps.map((item, index) => <button type="button" className={index === step ? 'active' : ''} aria-pressed={index === step} onClick={() => setStep(index)} key={item.title}><span>{item.time}</span>{item.title}</button>)}
        </div>
      </section>

      <section className="sw-tutor" aria-labelledby={`${direction.id}-tutor-title`}>
        <div className="sw-panel-head"><div><span>Cited tutor</span><strong id={`${direction.id}-tutor-title`}>Why are there two buses?</strong></div><IconSparkles size={18} aria-hidden="true" /></div>
        <blockquote><IconMessageCircle size={18} aria-hidden="true" /><p>The address bus says <em>where</em> to look; the data bus carries <em>what</em> was found. Separating them lets the request and response have distinct roles.</p></blockquote>
        <button type="button" className="sw-cite" onClick={() => setCitation(true)}><IconBook2 size={16} aria-hidden="true" /> View support · TLDR sample 0:08</button>
      </section>

      <section className="sw-recall" aria-labelledby={`${direction.id}-recall-title`}>
        <div className="sw-panel-head"><div><span>Active recall</span><strong id={`${direction.id}-recall-title`}>Check the sequence</strong></div><IconRefresh size={18} aria-hidden="true" /></div>
        <p>Before revealing the answer: what travels first, the address or the value?</p>
        <button type="button" className={recalled ? 'is-recalled' : ''} aria-pressed={recalled} onClick={() => setRecalled((value) => !value)}>{recalled ? <><IconCheck size={17} /> Address first · answer revealed</> : 'Reveal answer'}</button>
      </section>
    </article>
  )
}

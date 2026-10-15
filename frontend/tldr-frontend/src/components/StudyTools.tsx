import { useId, useMemo, useState } from 'react'
import {
  IconBookmark,
  IconBrain,
  IconCheck,
  IconCircleCheck,
  IconHelpCircle,
  IconListCheck,
  IconPlus,
  IconRotate,
  IconTrash,
} from '../icons'
import { api } from '../lib/api'
import { MathText } from './MathText'
import type { Course, StudyItem, StudyKind } from '../types'

type Props = {
  courseId: Course['id']
  items: StudyItem[]
  demo: boolean
  onItemsChange: (items: StudyItem[]) => void
  onNotice: (message: string) => void
}

const kinds: { kind: StudyKind; label: string; icon: typeof IconBrain }[] = [
  { kind: 'flashcard', label: 'Flashcards', icon: IconRotate },
  { kind: 'quiz', label: 'Quizzes', icon: IconHelpCircle },
  { kind: 'checklist', label: 'Checklists', icon: IconListCheck },
  { kind: 'bookmark', label: 'Bookmarks', icon: IconBookmark },
  { kind: 'confusion', label: 'Confusions', icon: IconBrain },
]

export function StudyTools({ courseId, items, demo, onItemsChange, onNotice }: Props) {
  const [kind, setKind] = useState<StudyKind>('flashcard')
  const [creating, setCreating] = useState(false)
  const filtered = useMemo(() => items.filter((item) => item.kind === kind), [items, kind])

  const update = async (item: StudyItem, patch: Partial<StudyItem>) => {
    const optimistic = { ...item, ...patch }
    onItemsChange(items.map((entry) => entry.id === item.id ? optimistic : entry))
    if (demo) {
      onNotice('Demo study edits are local to this page and are not saved.')
      return
    }
    try {
      const saved = await api.updateStudyItem(item.id, patch)
      onItemsChange(items.map((entry) => entry.id === item.id ? saved : entry))
    } catch (error) {
      onItemsChange(items)
      onNotice(error instanceof Error ? error.message : 'Study item could not be saved.')
    }
  }

  const remove = async (item: StudyItem) => {
    if (demo) {
      onItemsChange(items.filter((entry) => entry.id !== item.id))
      onNotice('Removed from this demo view only.')
      return
    }
    try {
      await api.deleteStudyItem(item.id)
      onItemsChange(items.filter((entry) => entry.id !== item.id))
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Study item could not be deleted.')
    }
  }

  const create = async (title: string, body: string) => {
    const item: Omit<StudyItem, 'id'> = {
      course: courseId,
      kind,
      title,
      body: kind === 'flashcard' ? '' : body,
      completed: false,
      data: kind === 'flashcard'
        ? { answer: body }
        : kind === 'quiz'
          ? { options: ['', '', ''], answer: '', attempts: [] }
          : kind === 'checklist'
            ? { items: [{ text: '', done: false }] }
            : {},
    }
    try {
      const saved = demo ? { ...item, id: `demo-study-${Date.now()}` } : await api.createStudyItem(item)
      onItemsChange([...items, saved])
      setCreating(false)
      if (demo) onNotice('Added to this demo view only.')
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Study item could not be added.')
    }
  }

  return (
    <section className="study-tools" aria-label="Study tools">
      <header className="workspace-header"><div><span className="quiet-label">Active recall</span><h1>Study tools</h1></div><button className="button primary" type="button" onClick={() => setCreating(true)}><IconPlus size={18} aria-hidden="true" /> New {kinds.find((entry) => entry.kind === kind)?.label.slice(0, -1)}</button></header>
      <nav className="study-tabs" aria-label="Study item types">
        {kinds.map((entry) => {
          const Icon = entry.icon
          const count = items.filter((item) => item.kind === entry.kind).length
          return <button type="button" className={entry.kind === kind ? 'study-tab active' : 'study-tab'} aria-current={entry.kind === kind ? 'page' : undefined} onClick={() => setKind(entry.kind)} key={entry.kind}><Icon size={18} aria-hidden="true" /><span>{entry.label}</span><small>{count}</small></button>
        })}
      </nav>

      {filtered.length === 0 ? (
        <div className="empty-state compact"><IconCircleCheck size={31} aria-hidden="true" /><h2>No {kinds.find((entry) => entry.kind === kind)?.label.toLowerCase()} yet</h2><p>Capture one from a source, lesson moment, or question you want to revisit.</p><button className="button" type="button" onClick={() => setCreating(true)}><IconPlus size={18} aria-hidden="true" /> Add one</button></div>
      ) : (
        <div className="study-grid">
          {filtered.map((item) => <StudyCard item={item} onUpdate={(patch) => void update(item, patch)} onDelete={() => void remove(item)} key={item.id} />)}
        </div>
      )}
      {creating && <NewStudyItem kind={kind} onClose={() => setCreating(false)} onCreate={(title, body) => void create(title, body)} />}
    </section>
  )
}

function StudyCard({ item, onUpdate, onDelete }: { item: StudyItem; onUpdate: (patch: Partial<StudyItem>) => void; onDelete: () => void }) {
  const answerId = useId()
  const [revealed, setRevealed] = useState(false)
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(item.title)
  const [body, setBody] = useState(item.body ?? '')
  const [answerDraft, setAnswerDraft] = useState(typeof item.data.answer === 'string' && item.data.answer ? item.data.answer : item.body ?? '')
  const [quizAnswer, setQuizAnswer] = useState('')
  const answer = typeof item.data.answer === 'string' ? item.data.answer : ''
  const options = Array.isArray(item.data.options) ? item.data.options.filter((option): option is string => typeof option === 'string') : []
  const checklist = Array.isArray(item.data.items) ? item.data.items.filter((entry): entry is { text: string; done: boolean } => typeof entry === 'object' && entry !== null && 'text' in entry && 'done' in entry) : []

  const save = () => {
    onUpdate(item.kind === 'flashcard' ? { title, body: '', data: { ...item.data, answer: answerDraft } } : { title, body })
    setEditing(false)
  }

  return (
    <article className={`study-card ${item.completed ? 'completed' : ''}`}>
      <header><span className="study-kind">{item.kind}</span><div className="study-actions"><button className="icon-button" type="button" aria-label={item.completed ? 'Mark incomplete' : 'Mark complete'} onClick={() => onUpdate({ completed: !item.completed })}><IconCheck size={17} /></button><button className="icon-button" type="button" aria-label={`Delete ${item.title}`} onClick={onDelete}><IconTrash size={17} /></button></div></header>
      {editing ? (
        <div className="study-edit"><label>{item.kind === 'flashcard' ? 'Question' : 'Title'}<input value={title} onChange={(event) => setTitle(event.target.value)} /></label>{item.kind === 'flashcard' ? <label>Answer<textarea rows={4} value={answerDraft} onChange={(event) => setAnswerDraft(event.target.value)} /></label> : <label>Notes<textarea rows={4} value={body} onChange={(event) => setBody(event.target.value)} /></label>}<MathEditPreview question={title} answer={item.kind === 'flashcard' ? answerDraft : body} /><div className="button-row end"><button className="button compact" type="button" onClick={() => setEditing(false)}>Cancel</button><button className="button primary compact" type="button" onClick={save}>Save</button></div></div>
      ) : (
        <div className="study-card-main"><h2><MathText text={item.title} /></h2>{body && <p><MathText text={body} /></p>}{item.kind === 'flashcard' && <div id={answerId} className={revealed ? 'flash-answer visible' : 'flash-answer'}><small>{revealed ? 'Answer' : 'Answer hidden'}</small>{revealed && <strong><MathText text={answer || 'Add an answer in edit mode.'} /></strong>}</div>}</div>
      )}
      {item.kind === 'flashcard' && !editing && <button className="button compact" type="button" aria-expanded={revealed} aria-controls={answerId} onClick={() => setRevealed((value) => !value)}>{revealed ? 'Hide answer' : 'Reveal answer'}</button>}
      {item.kind === 'quiz' && options.length > 0 && <div className="quiz-options">{options.map((option) => <button type="button" className={quizAnswer === option ? (option === answer ? 'correct' : 'incorrect') : ''} onClick={() => setQuizAnswer(option)} key={option}><MathText text={option} />{quizAnswer === option && option === answer && <IconCheck size={16} aria-label="Correct" />}</button>)}</div>}
      {item.kind === 'checklist' && <div className="checklist">{checklist.map((entry, index) => <label key={`${entry.text}-${index}`}><input type="checkbox" checked={entry.done} onChange={() => onUpdate({ data: { ...item.data, items: checklist.map((candidate, candidateIndex) => candidateIndex === index ? { ...candidate, done: !candidate.done } : candidate) } })} /><MathText text={entry.text || 'Untitled checklist item'} /></label>)}</div>}
      {!editing && <button className="text-button" type="button" onClick={() => setEditing(true)}>{item.kind === 'flashcard' ? 'Edit card' : 'Edit notes'}</button>}
    </article>
  )
}

function NewStudyItem({ kind, onClose, onCreate }: { kind: StudyKind; onClose: () => void; onCreate: (title: string, body: string) => void }) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="modal small" role="dialog" aria-modal="true" aria-labelledby="new-study-title"><header><div><span className="quiet-label">{kind}</span><h2 id="new-study-title">Add a study item</h2></div></header><form onSubmit={(event) => { event.preventDefault(); if (title.trim()) onCreate(title.trim(), body.trim()) }}><label>{kind === 'flashcard' ? 'Question' : 'Title'}<input autoFocus value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>{kind === 'flashcard' ? 'Answer' : 'Notes'}<textarea rows={5} value={body} onChange={(event) => setBody(event.target.value)} /></label><MathEditPreview question={title} answer={body} /><div className="button-row end"><button className="button" type="button" onClick={onClose}>Cancel</button><button className="button primary" type="submit" disabled={!title.trim()}>Add item</button></div></form></section></div>
  )
}

function MathEditPreview({ question, answer }: { question: string; answer: string }) {
  return <details className="math-edit-preview"><summary>Preview math</summary><small>{String.raw`Use \(x^2\) inline or \[\frac{1}{2}\] for a display equation.`}</small><div><MathText text={question} /></div><div><MathText text={answer} /></div></details>
}

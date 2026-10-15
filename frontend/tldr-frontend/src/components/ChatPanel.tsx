import { useCallback, useEffect, useRef, useState } from 'react'
import {
  IconBook2,
  IconChevronDown,
  IconMessageCircle,
  IconPlayerStop,
  IconSend,
  IconSparkles,
  IconX,
} from '../icons'
import { api } from '../lib/api'
import { demoMessages } from '../data/demo'
import { MathText } from './MathText'
import type { Citation, CitationTarget, Conversation, Course, Job, Message, Region, VideoContext } from '../types'

type Props = {
  courseId: Course['id']
  courseName: string
  conversations: Conversation[]
  jobs: Job[]
  demo: boolean
  generationEnabled?: boolean
  selectedRegionIds: Region['id'][]
  videoContext?: VideoContext
  onClearVideoContext: () => void
  onConversationsChange: (items: Conversation[]) => void
  onJobCreated: (job: Job) => void
  onCitation: (target: CitationTarget) => void
  onNotice: (message: string) => void
}

export function ChatPanel({
  courseId,
  courseName,
  conversations,
  jobs,
  demo,
  generationEnabled,
  selectedRegionIds,
  videoContext,
  onClearVideoContext,
  onConversationsChange,
  onJobCreated,
  onCitation,
  onNotice,
}: Props) {
  const [conversationId, setConversationId] = useState<Conversation['id'] | undefined>(conversations[0]?.id)
  const [messages, setMessages] = useState<Message[]>(demo ? demoMessages : [])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(!demo)
  const [submitting, setSubmitting] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const conversationRef = useRef(conversationId)
  conversationRef.current = conversationId

  useEffect(() => {
    setConversationId((current) => conversations.some((entry) => entry.id === current) ? current : conversations[0]?.id)
  }, [conversations])

  useEffect(() => {
    eventSourceRef.current?.close()
    if (demo) {
      setMessages(courseId === 'demo-transport' ? demoMessages : [])
      setLoading(false)
      return
    }
    if (!conversationId) {
      setMessages([])
      setLoading(false)
      return
    }
    const controller = new AbortController()
    let current = true
    setLoading(true)
    api.messages(conversationId, controller.signal)
      .then((items) => { if (current) setMessages(items) })
      .catch((error) => { if (current && error instanceof Error && error.name !== 'AbortError') onNotice(error.message) })
      .finally(() => { if (current) setLoading(false) })
    return () => {
      current = false
      controller.abort()
      eventSourceRef.current?.close()
    }
  }, [conversationId, courseId, demo, onNotice])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const ensureConversation = async () => {
    const existing = conversations.find((entry) => entry.id === conversationId) ?? conversations[0]
    if (existing) return existing
    const created = await api.createConversation(courseId)
    onConversationsChange([...conversations, created])
    conversationRef.current = created.id
    setConversationId(created.id)
    return created
  }

  const refreshMessages = useCallback(async (id: Conversation['id']) => {
    try {
      const next = await api.messages(id)
      if (conversationRef.current === id) setMessages(next)
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'Messages could not be refreshed.')
    }
  }, [onNotice])

  const hasPending = messages.some((message) => message.status === 'pending')
  // Course jobs prompt refreshes after a retry, but only this conversation's
  // pending messages can disable its composer. Paused jobs are terminal waits.
  const hasActiveChatJob = jobs.some((job) => job.kind === 'chat' && ['queued', 'running'].includes(job.status))
  const sending = submitting || hasPending
  const savingOnly = !demo && generationEnabled === false

  useEffect(() => {
    if (demo || !conversationId || (!hasPending && !hasActiveChatJob)) return
    const poll = window.setInterval(() => { void refreshMessages(conversationId) }, 2500)
    return () => window.clearInterval(poll)
  }, [conversationId, demo, hasActiveChatJob, hasPending, refreshMessages])

  const startStream = (conversation: Conversation, job: Job) => {
    eventSourceRef.current?.close()
    const stream = new EventSource(api.streamUrl(conversation.id, job.id))
    eventSourceRef.current = stream

    stream.addEventListener('message', (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as Message
        if (conversationRef.current === conversation.id) setMessages((items) => [...items.filter((item) => item.id !== payload.id), payload])
      } catch {
        onNotice('The assistant response arrived in an unreadable format.')
      }
    })
    stream.addEventListener('done', () => {
      stream.close()
      if (eventSourceRef.current === stream) eventSourceRef.current = null
      void refreshMessages(conversation.id)
    })
    stream.addEventListener('error', (event) => {
      if (event instanceof MessageEvent) {
        try {
          const payload = JSON.parse(event.data) as { detail?: string }
          if (payload.detail) onNotice(payload.detail)
        } catch {
          onNotice('The response stream ended before completion. Reloaded messages remain available.')
        }
        stream.close()
        if (eventSourceRef.current === stream) eventSourceRef.current = null
        void refreshMessages(conversation.id)
      }
    })
  }

  const send = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!draft.trim() || sending || demo) return
    setSubmitting(true)
    try {
      const conversation = await ensureConversation()
      const { message, job } = await api.sendMessage(conversation.id, {
        content: draft.trim(),
        region_ids: selectedRegionIds,
        context: videoContext ? {
          revision_id: videoContext.revision_id,
          scene_id: videoContext.scene_id,
          time_seconds: videoContext.time_seconds,
          object_ids: videoContext.object_ids,
        } : undefined,
      })
      if (conversationRef.current === conversation.id) setMessages((items) => [...items, message])
      setDraft('')
      onJobCreated(job)
      await refreshMessages(conversation.id)
      if (conversationRef.current === conversation.id) startStream(conversation, job)
    } catch (error) {
      onNotice(error instanceof Error ? error.message : 'The question could not be sent.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <aside className="chat-panel" aria-labelledby="chat-heading">
      <header className="chat-header">
        <div>
          <span className="quiet-label">Course conversation</span>
          <h2 id="chat-heading">Ask with evidence</h2>
        </div>
        {conversations.length > 1 && (
          <label className="conversation-select">
            <span className="sr-only">Conversation</span>
            <select value={String(conversationId ?? '')} onChange={(event) => setConversationId(conversations.find((conversation) => String(conversation.id) === event.target.value)?.id)}>
              {conversations.map((conversation) => <option value={String(conversation.id)} key={conversation.id}>{conversation.title}</option>)}
            </select>
            <IconChevronDown size={16} aria-hidden="true" />
          </label>
        )}
      </header>

      <div className="chat-context" aria-label="Attached context">
        <div>
          <IconBook2 size={16} aria-hidden="true" />
          <span>{selectedRegionIds.length ? `${selectedRegionIds.length} source region${selectedRegionIds.length === 1 ? '' : 's'}` : courseName}</span>
        </div>
        {videoContext && (
          <div className="context-chip">
            <IconPlayerStop size={15} aria-hidden="true" />
            <span>{videoContext.label}</span>
            <button type="button" aria-label="Remove video context" onClick={onClearVideoContext}><IconX size={14} /></button>
          </div>
        )}
      </div>

      <div className="message-list" ref={scrollRef} aria-live="polite" aria-busy={loading || sending}>
        {loading ? (
          <div className="message-skeleton" aria-label="Loading conversation"><i /><i /><i /></div>
        ) : messages.length === 0 ? (
          <div className="chat-empty">
            <IconMessageCircle size={30} aria-hidden="true" />
            <strong>Start with what you can see</strong>
            <p>Mark a source region, then ask for an explanation, comparison, or worked example.</p>
          </div>
        ) : messages.map((message) => (
          <article className={`message ${message.role}`} key={message.id}>
            <div className="message-meta">
              <span>{message.role === 'assistant' ? 'Tutor' : 'You'}</span>
              {message.curated && <small>Curated example</small>}
              {message.status === 'pending' && <small>{savingOnly ? 'Saved; waiting for AI availability' : 'Waiting for validated citations'}</small>}
              {message.status === 'error' && <small>Could not complete</small>}
            </div>
            <p><MathText text={message.content} /></p>
            {message.citations.length > 0 && <CitationList citations={message.citations} onCitation={onCitation} />}
          </article>
        ))}
        {sending && (
          <div className="assistant-working" role="status">
            <IconSparkles size={17} aria-hidden="true" />
            <span>{savingOnly ? 'Saving your question and selected context' : 'Checking the answer against your sources'}</span>
          </div>
        )}
      </div>

      <form className="chat-composer" onSubmit={send}>
        {demo && <p className="demo-readonly">Demo conversation is read-only and makes no API requests.</p>}
        {savingOnly && <p className="demo-readonly">AI answers are paused. Save your question with its source or lesson context, then retry it from Activity after setup or the free quota resets.</p>}
        <label htmlFor="chat-input">Question</label>
        <textarea
          id="chat-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={demo ? 'Open the local app to ask about your own course.' : 'Ask about the source or selected lesson moment'}
          disabled={demo}
          rows={3}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              event.currentTarget.form?.requestSubmit()
            }
          }}
        />
        <div className="composer-footer">
          <span>Enter to {savingOnly ? 'save' : 'send'}. Shift + Enter for a new line.</span>
          <button className="send-button" type="submit" aria-label={savingOnly ? 'Save question' : 'Send question'} disabled={demo || sending || !draft.trim()}><IconSend size={19} /></button>
        </div>
      </form>
    </aside>
  )
}

function CitationList({ citations, onCitation }: { citations: Citation[]; onCitation: (target: CitationTarget) => void }) {
  return (
    <ol className="citations" aria-label="Answer citations">
      {citations.map((citation, index) => (
        <li key={`${citation.page_id}-${citation.region_id ?? index}`}>
          <button type="button" onClick={() => onCitation({ sourceId: citation.source_id, pageId: citation.page_id, regionId: citation.region_id })}>
            <span>[{index + 1}] {citation.source_title}, p. {citation.page_number}{citation.visual ? ' (visual evidence)' : ''}</span>
            {citation.quote && <q><MathText text={citation.quote} /></q>}
          </button>
        </li>
      ))}
    </ol>
  )
}

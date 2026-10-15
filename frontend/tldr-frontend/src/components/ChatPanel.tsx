import { useCallback, useEffect, useRef, useState } from 'react'
import { IconBook2, IconMessageCircle, IconPlayerStop, IconSend, IconSparkles, IconX } from '../icons'
import { api } from '../lib/api'
import { attachChatContext, completeChatSend, createLocalChatSession, createSavedChatSession, deriveConversationTitle, reconcileConversationSessions, updateChatSession, type ChatSessionMap } from '../lib/chat'
import { demoMessages } from '../data/demo'
import { MathText } from './MathText'
import type { Citation, CitationTarget, Conversation, Course, Job, Message, Region, VideoContext } from '../types'
import './ChatPanel.css'

export type ChatAttachmentRequest = { id: number; videoContext?: VideoContext; regionIds?: Region['id'][] }

type Props = {
  active: boolean
  attachmentRequest?: ChatAttachmentRequest
  courseId: Course['id']
  courseName: string
  conversations: Conversation[]
  jobs: Job[]
  demo: boolean
  generationEnabled?: boolean
  onConversationCreated: (conversation: Conversation) => void
  onJobCreated: (job: Job) => void
  onCitation: (target: CitationTarget) => void
  onNotice: (message: string) => void
  onRegionSelectionChange?: (ids: Region['id'][]) => void
}

// Course identity owns the entire session store and every in-flight request.
export function ChatPanel(props: Props) {
  return <CourseChatPanel key={`${typeof props.courseId}:${props.courseId}:${props.demo}`} {...props} />
}

function CourseChatPanel(props: Props) {
  const { active, attachmentRequest, courseId, courseName, conversations, demo, generationEnabled, onCitation } = props
  const [sessions, setSessions] = useState<ChatSessionMap>(() => Object.fromEntries(conversations.map((conversation) => {
    const session = createSavedChatSession(conversation, demo && courseId === 'demo-transport' ? demoMessages : [])
    return [session.key, { ...session, loaded: demo || session.loaded }]
  })))
  const [selectedKey, setSelectedKey] = useState<string>()
  const sessionsRef = useRef(sessions)
  const selectedRef = useRef(selectedKey)
  const lastSelectedRef = useRef<string>()
  const propsRef = useRef(props)
  propsRef.current = props
  const lifetime = useRef(0)
  const requestSequence = useRef(0)
  const controllers = useRef(new Set<AbortController>())
  const pendingLoads = useRef(new Map<string, number>())
  const streams = useRef(new Map<string, EventSource>())
  const consumedAttachments = useRef(new Set<number>())
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const newChatRef = useRef<HTMLButtonElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLElement>(null)
  const focusComposer = useRef(false)
  const mutate = useCallback((change: (store: ChatSessionMap) => ChatSessionMap) => {
    const next = change(sessionsRef.current)
    sessionsRef.current = next
    setSessions(next)
  }, [])
  const select = useCallback((key?: string) => {
    selectedRef.current = key
    if (key) lastSelectedRef.current = key
    setSelectedKey(key)
  }, [])

  useEffect(() => {
    lifetime.current += 1
    const requests = controllers.current
    const connections = streams.current
    const loads = pendingLoads.current
    return () => {
      lifetime.current += 1
      requests.forEach((controller) => controller.abort())
      requests.clear()
      connections.forEach((stream) => stream.close())
      connections.clear()
      loads.clear()
    }
  }, [])

  const awaitingCreation = Object.values(sessions).some((session) => session.submitting && session.conversationId === undefined)
  useEffect(() => {
    mutate((store) => reconcileConversationSessions(store, conversations))
  }, [conversations, mutate, awaitingCreation])

  const refresh = useCallback(async (key: string, showLoading = false) => {
    const original = sessionsRef.current[key]
    if (demo || !original || original.conversationId === undefined || original.submitting) return
    if (!showLoading && pendingLoads.current.has(key)) return
    const epoch = lifetime.current
    const requestId = ++requestSequence.current
    const controller = new AbortController()
    controllers.current.add(controller)
    pendingLoads.current.set(key, requestId)
    mutate((store) => updateChatSession(store, key, { loadRequestId: requestId, loading: showLoading, ...(showLoading ? { loadError: undefined } : {}) }))
    try {
      const messages = await api.messages(original.conversationId, controller.signal)
      if (epoch !== lifetime.current) return
      mutate((store) => store[key]?.loadRequestId === requestId
        ? updateChatSession(store, key, { messages, loaded: true, loading: false, loadError: undefined }) : store)
    } catch (error) {
      if (epoch !== lifetime.current || controller.signal.aborted) return
      mutate((store) => store[key]?.loadRequestId === requestId
        ? updateChatSession(store, key, { loading: false, loadError: error instanceof Error ? error.message : 'Messages could not be loaded.' }) : store)
    } finally {
      controllers.current.delete(controller)
      if (pendingLoads.current.get(key) === requestId) pendingLoads.current.delete(key)
    }
  }, [demo, mutate])

  useEffect(() => {
    if (selectedKey && !sessionsRef.current[selectedKey]?.loaded) void refresh(selectedKey, true)
  }, [selectedKey, refresh])

  // Read the latest sessions/jobs inside one stable timer; parent rerenders do not restart polling.
  useEffect(() => {
    if (demo) return
    const timer = window.setInterval(() => {
      const activeJobs = propsRef.current.jobs.some((job) => job.kind === 'chat' && ['queued', 'running'].includes(job.status))
      Object.values(sessionsRef.current).forEach((session) => {
        if (session.loaded && !session.loading && !session.submitting && (activeJobs || session.messages.some((message) => message.status === 'pending'))) void refresh(session.key)
      })
    }, 2500)
    return () => window.clearInterval(timer)
  }, [demo, refresh])

  useEffect(() => {
    if (!attachmentRequest || consumedAttachments.current.has(attachmentRequest.id)) return
    consumedAttachments.current.add(attachmentRequest.id)
    let key = selectedRef.current ?? lastSelectedRef.current
    if (!key || !sessionsRef.current[key]) {
      const session = createLocalChatSession()
      key = session.key
      mutate((store) => ({ ...store, [session.key]: session }))
    }
    const targetKey = key
    mutate((store) => updateChatSession(store, targetKey, (session) => attachChatContext(session, attachmentRequest)))
    focusComposer.current = true
    select(key)
  }, [attachmentRequest, mutate, select])

  const session = selectedKey ? sessions[selectedKey] : undefined
  useEffect(() => {
    if (active) propsRef.current.onRegionSelectionChange?.(session?.regionIds ?? [])
  }, [active, selectedKey, session?.regionIds])
  useEffect(() => {
    if (active && selectedKey && focusComposer.current) {
      focusComposer.current = false
      composerRef.current?.focus()
    }
  }, [active, selectedKey, attachmentRequest])
  useEffect(() => {
    if (active) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [active, selectedKey, session?.messages])

  useEffect(() => {
    if (!active || !selectedKey) return
    const back = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || event.defaultPrevented) return
      if (!(event.target instanceof Node) || !panelRef.current?.contains(event.target)) return
      // Higher-level overlays own Escape before the chat list does.
      const overlay = Array.from(document.querySelectorAll<HTMLElement>('[role="dialog"], [role="alertdialog"], [role="menu"], dialog[open]')).some((element) => element.getClientRects().length > 0)
      if (overlay) return
      event.preventDefault()
      select(undefined)
      newChatRef.current?.focus()
    }
    document.addEventListener('keydown', back)
    return () => document.removeEventListener('keydown', back)
  }, [active, selectedKey, select])

  const startStream = (key: string, id: Conversation['id'], job: Job, epoch: number) => {
    streams.current.get(key)?.close()
    const stream = new EventSource(api.streamUrl(id, job.id))
    streams.current.set(key, stream)
    const valid = () => epoch === lifetime.current && streams.current.get(key) === stream
    const finish = () => {
      if (!valid()) return
      stream.close()
      streams.current.delete(key)
      void refresh(key)
    }
    stream.addEventListener('message', (event) => {
      if (!valid()) return
      try {
        const message = JSON.parse((event as MessageEvent).data) as Message
        if (message.conversation !== id || !Array.isArray(message.citations) || typeof message.content !== 'string') throw new Error('Invalid response')
        mutate((store) => updateChatSession(store, key, (current) => ({ ...current, loading: false, loadRequestId: ++requestSequence.current, messages: [...current.messages.filter((item) => item.id !== message.id), message] })))
      } catch {
        mutate((store) => updateChatSession(store, key, { error: 'The assistant response arrived in an unreadable format.' }))
      }
    })
    stream.addEventListener('done', finish)
    stream.addEventListener('error', (event) => {
      if (!valid()) return
      if (event instanceof MessageEvent) {
        try {
          const payload = JSON.parse(event.data) as { detail?: string }
          if (payload.detail) mutate((store) => updateChatSession(store, key, { error: payload.detail }))
        } catch {
          mutate((store) => updateChatSession(store, key, { error: 'The response stream ended before completion. Saved messages remain available.' }))
        }
      }
      finish()
    })
  }

  const send = async (event: React.FormEvent) => {
    event.preventDefault()
    const key = selectedRef.current
    const original = key ? sessionsRef.current[key] : undefined
    if (!key || !original || !original.loaded || !original.draft.trim() || original.submitting || original.loading || original.messages.some((message) => message.status === 'pending') || demo) return
    const epoch = lifetime.current
    const requestId = ++requestSequence.current
    const content = original.draft.trim()
    const regionIds = [...original.regionIds]
    const context = original.videoContext ? { revision_id: original.videoContext.revision_id, scene_id: original.videoContext.scene_id, time_seconds: original.videoContext.time_seconds, object_ids: original.videoContext.object_ids ? [...original.videoContext.object_ids] : undefined } : undefined
    const valid = () => epoch === lifetime.current && sessionsRef.current[key]?.sendRequestId === requestId
    streams.current.get(key)?.close()
    streams.current.delete(key)
    pendingLoads.current.delete(key)
    mutate((store) => updateChatSession(store, key, { submitting: true, error: undefined, sendRequestId: requestId, loadRequestId: ++requestSequence.current }))
    try {
      let id = original.conversationId
      if (id === undefined) {
        const created = await api.createConversation(courseId, deriveConversationTitle(content))
        if (!valid()) return
        id = created.id
        mutate((store) => updateChatSession(store, key, { conversationId: id, title: created.title, createdAt: created.created_at }))
        propsRef.current.onConversationCreated(created)
      }
      const { message, job } = await api.sendMessage(id, { content, region_ids: regionIds, context })
      if (!valid()) return
      mutate((store) => updateChatSession(store, key, (current) => completeChatSend(current, original, message)))
      propsRef.current.onJobCreated(job)
      startStream(key, id, job, epoch)
      void refresh(key, true)
    } catch (error) {
      if (valid()) mutate((store) => updateChatSession(store, key, { submitting: false, error: error instanceof Error ? error.message : 'The question could not be sent.' }))
    }
  }

  const savingOnly = !demo && generationEnabled === false
  const sending = Boolean(session?.submitting || session?.messages.some((message) => message.status === 'pending'))
  const open = (key: string) => { focusComposer.current = true; select(key) }
  const newChat = () => {
    const created = createLocalChatSession()
    mutate((store) => ({ ...store, [created.key]: created }))
    open(created.key)
  }
  const chatList = Object.values(sessions).sort((a, b) => (Date.parse(b.createdAt ?? '') || 0) - (Date.parse(a.createdAt ?? '') || 0))

  return (
    <section className="chat-panel" ref={panelRef} aria-label="Tutor chats">
      <header className="chat-header">
        <div>{session && <button type="button" className="chat-back" onClick={() => { select(undefined); newChatRef.current?.focus() }}>← Back to chats</button>}<h2>{session ? session.title : 'Chats'}</h2></div>
        <button type="button" className="button chat-new" ref={newChatRef} onClick={newChat}>New chat</button>
      </header>
      {!session ? <div className="chat-history">
        <p className="chat-history-intro">Your conversations for {courseName}.</p>
        {chatList.length === 0 ? <div className="chat-empty"><IconMessageCircle size={30} aria-hidden="true" /><strong>No chats yet</strong><p>Start a new chat to ask about your course.</p></div> : <ul aria-label="Chats">{chatList.map((chat) => <li key={chat.key}><button type="button" onClick={() => open(chat.key)}><strong>{chat.title}</strong><span>{chat.createdAt && !Number.isNaN(Date.parse(chat.createdAt)) ? <time dateTime={chat.createdAt}>{new Date(chat.createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</time> : 'Date unavailable'}{chat.conversationId === undefined && ' · Unsent'}{chat.submitting && ' · Sending'}</span></button></li>)}</ul>}
      </div> : <>
        <div className="chat-context" aria-label="Attached context">
          <div><IconBook2 size={16} aria-hidden="true" /><span>{courseName}</span></div>
          {session.regionIds.length > 0 && <div className="context-chip"><span>{session.regionIds.length} source region{session.regionIds.length === 1 ? '' : 's'}</span><button type="button" aria-label="Remove source regions" onClick={() => mutate((store) => updateChatSession(store, session.key, (current) => ({ ...current, regionIds: [], contextVersion: current.contextVersion + 1 })))}><IconX size={14} /></button></div>}
          {session.videoContext && <div className="context-chip"><IconPlayerStop size={15} aria-hidden="true" /><span>{session.videoContext.label}</span><button type="button" aria-label="Remove video context" onClick={() => mutate((store) => updateChatSession(store, session.key, (current) => ({ ...current, videoContext: undefined, contextVersion: current.contextVersion + 1 })))}><IconX size={14} /></button></div>}
        </div>
        <div className="message-list" ref={scrollRef} aria-live="polite" aria-busy={session.loading || sending}>
          {session.loading ? <div className="message-skeleton" aria-label="Loading conversation"><i /><i /><i /></div> : session.messages.length === 0 ? <div className="chat-empty"><IconMessageCircle size={30} aria-hidden="true" /><strong>Start with what you can see</strong><p>Attach a source region or lesson moment, then ask for an explanation, comparison, or worked example.</p></div> : session.messages.map((message) => <article className={`message ${message.role}`} key={message.id}>
            <div className="message-meta"><span>{message.role === 'assistant' ? 'Tutor' : 'You'}</span>{message.curated && <small>Curated example</small>}{message.status === 'pending' && <small>{savingOnly ? 'Saved; waiting for AI availability' : 'Waiting for validated citations'}</small>}{message.status === 'error' && <small>Could not complete</small>}</div>
            <p><MathText text={message.content} /></p>
            {message.citations.length > 0 && <CitationList citations={message.citations} onCitation={onCitation} />}
          </article>)}
          {sending && <div className="assistant-working" role="status"><IconSparkles size={17} aria-hidden="true" /><span>{savingOnly ? 'Saving your question and selected context' : 'Checking the answer against your sources'}</span></div>}
          {(session.error || session.loadError) && <div className="chat-error" role="alert"><p>{session.error || session.loadError}</p>{session.loadError && <button className="button" type="button" onClick={() => void refresh(session.key, true)}>Retry loading</button>}</div>}
        </div>
        <form className="chat-composer" onSubmit={send}>
          {demo && <p className="demo-readonly">Demo conversation is read-only and makes no API requests.</p>}
          {savingOnly && <p className="demo-readonly">AI answers are paused. Save your question with its source or lesson context, then retry it from Activity after setup or the free quota resets.</p>}
          <label htmlFor="chat-input">Question</label>
          <textarea id="chat-input" ref={composerRef} value={session.draft} onChange={(event) => { const value = event.target.value; mutate((store) => updateChatSession(store, session.key, (current) => ({ ...current, draft: value, draftVersion: current.draftVersion + 1 }))) }} placeholder={demo ? 'Open the local app to ask about your own course.' : 'Ask about the source or selected lesson moment'} disabled={demo} rows={3} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} />
          <div className="composer-footer"><span>Enter to {savingOnly ? 'save' : 'send'}. Shift + Enter for a new line.</span><button className="send-button" type="submit" aria-label={savingOnly ? 'Save question' : 'Send question'} disabled={demo || sending || session.loading || !session.loaded || !session.draft.trim()}><IconSend size={19} /></button></div>
        </form>
      </>}
    </section>
  )
}

function CitationList({ citations, onCitation }: { citations: Citation[]; onCitation: (target: CitationTarget) => void }) {
  return <ol className="citations" aria-label="Answer citations">{citations.map((citation, index) => <li key={`${citation.page_id}-${citation.region_id ?? index}`}><button type="button" onClick={() => onCitation({ sourceId: citation.source_id, pageId: citation.page_id, regionId: citation.region_id })}><span>[{index + 1}] {citation.source_title}, p. {citation.page_number}{citation.visual ? ' (visual evidence)' : ''}</span>{citation.quote && <q><MathText text={citation.quote} /></q>}</button></li>)}</ol>
}

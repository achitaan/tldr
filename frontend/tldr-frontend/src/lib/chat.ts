import type { Conversation, Message, Region, VideoContext } from '../types'

export type ChatSession = {
  key: string
  conversationId?: Conversation['id']
  title: string
  createdAt?: string
  draft: string
  draftVersion: number
  contextVersion: number
  regionIds: Region['id'][]
  videoContext?: VideoContext
  messages: Message[]
  loaded: boolean
  loading: boolean
  submitting: boolean
  error?: string
  loadError?: string
  loadRequestId?: number
  sendRequestId?: number
}

export type ChatSessionMap = Record<string, ChatSession>
export type SessionRequestField = 'loadRequestId' | 'sendRequestId'

let localSessionSequence = 0

export function savedSessionKey(id: Conversation['id']): string {
  return `saved:${typeof id}:${String(id)}`
}

export function createLocalSessionKey(): string {
  localSessionSequence += 1
  const randomId = globalThis.crypto?.randomUUID?.()
  return `local:${randomId ?? `${Date.now().toString(36)}-${localSessionSequence.toString(36)}`}`
}

export function createSavedChatSession(conversation: Conversation, messages: Message[] = []): ChatSession {
  return {
    key: savedSessionKey(conversation.id),
    conversationId: conversation.id,
    title: conversation.title,
    createdAt: conversation.created_at,
    draft: '',
    draftVersion: 0,
    contextVersion: 0,
    regionIds: [],
    messages,
    loaded: messages.length > 0,
    loading: false,
    submitting: false,
  }
}

export function createLocalChatSession(key = createLocalSessionKey()): ChatSession {
  return {
    key,
    title: 'New chat',
    createdAt: new Date().toISOString(),
    draft: '',
    draftVersion: 0,
    contextVersion: 0,
    regionIds: [],
    messages: [],
    loaded: true,
    loading: false,
    submitting: false,
  }
}

export function reconcileConversationSessions(sessions: ChatSessionMap, conversations: Conversation[]): ChatSessionMap {
  let next = sessions
  // A course poll can observe a committed conversation before the create
  // response gives its ID to the local session. Wait for that adoption before
  // exposing unknown IDs, so one conversation never acquires two session keys.
  const awaitingCreation = Object.values(sessions).some((session) => session.submitting && session.conversationId === undefined)
  for (const conversation of conversations) {
    const existing = Object.values(next).find((session) => session.conversationId === conversation.id)
    if (existing) {
      if (existing.title === conversation.title && existing.createdAt === conversation.created_at) continue
      if (next === sessions) next = { ...sessions }
      next[existing.key] = { ...existing, title: conversation.title, createdAt: conversation.created_at }
      continue
    }
    if (awaitingCreation) continue
    if (next === sessions) next = { ...sessions }
    const session = createSavedChatSession(conversation)
    next[session.key] = session
  }
  return next
}

export function updateChatSession(
  sessions: ChatSessionMap,
  key: string,
  update: Partial<ChatSession> | ((session: ChatSession) => ChatSession),
): ChatSessionMap {
  const current = sessions[key]
  if (!current) return sessions
  const nextSession = typeof update === 'function' ? update(current) : { ...current, ...update }
  if (nextSession === current) return sessions
  return { ...sessions, [key]: nextSession }
}

export function finishSessionRequest(
  sessions: ChatSessionMap,
  key: string,
  field: SessionRequestField,
  requestId: number,
  update: (session: ChatSession) => ChatSession,
): ChatSessionMap {
  const session = sessions[key]
  if (!session || session[field] !== requestId) return sessions
  return updateChatSession(sessions, key, update)
}

export function attachChatContext(session: ChatSession, attachment: { regionIds?: Region['id'][]; videoContext?: VideoContext }): ChatSession {
  return {
    ...session,
    contextVersion: session.contextVersion + 1,
    ...(attachment.regionIds !== undefined ? { regionIds: [...attachment.regionIds] } : {}),
    ...(attachment.videoContext !== undefined ? { videoContext: { ...attachment.videoContext, object_ids: attachment.videoContext.object_ids ? [...attachment.videoContext.object_ids] : undefined } } : {}),
  }
}

export function completeChatSend(current: ChatSession, submitted: ChatSession, message: Message): ChatSession {
  return {
    ...current,
    submitting: false,
    loaded: true,
    messages: [...current.messages.filter((item) => item.id !== message.id), message],
    ...(current.draftVersion === submitted.draftVersion ? { draft: '' } : {}),
    ...(current.contextVersion === submitted.contextVersion ? { regionIds: [], videoContext: undefined } : {}),
  }
}

export function deriveConversationTitle(question: string, maxLength = 72): string {
  const normalized = question.replace(/\s+/g, ' ').trim()
  if (!normalized) return 'New chat'
  if (normalized.length <= maxLength) return normalized
  const candidate = normalized.slice(0, maxLength + 1)
  const lastSpace = candidate.lastIndexOf(' ')
  const cutAt = lastSpace >= Math.floor(maxLength * 0.6) ? lastSpace : maxLength
  return `${normalized.slice(0, cutAt).trimEnd()}…`
}

export function sortConversationsNewestFirst(conversations: Conversation[]): Conversation[] {
  return conversations
    .map((conversation, index) => ({ conversation, index, timestamp: parseTimestamp(conversation.created_at) }))
    .sort((left, right) => right.timestamp - left.timestamp || left.index - right.index)
    .map(({ conversation }) => conversation)
}

function parseTimestamp(value?: string): number {
  if (!value) return Number.NEGATIVE_INFINITY
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? Number.NEGATIVE_INFINITY : timestamp
}


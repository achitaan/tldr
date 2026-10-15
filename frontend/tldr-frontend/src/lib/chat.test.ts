import { describe, expect, it } from 'vitest'
import type { Conversation } from '../types'
import {
  attachChatContext,
  completeChatSend,
  createLocalChatSession,
  deriveConversationTitle,
  finishSessionRequest,
  reconcileConversationSessions,
  sortConversationsNewestFirst,
  updateChatSession,
} from './chat'

describe('chat session helpers', () => {
  it('keeps a local session identity when a course poll sees its committed ID before the create response', () => {
    const local = { ...createLocalChatSession('local:creating'), submitting: true, draft: 'A newer local draft' }
    const created: Conversation = { id: 42, course: 7, title: 'First question' }
    const pending = reconcileConversationSessions({ [local.key]: local }, [created])
    expect(Object.keys(pending)).toEqual([local.key])
    const adopted = updateChatSession(pending, local.key, { conversationId: created.id })
    const resolved = reconcileConversationSessions(adopted, [created])
    expect(Object.keys(resolved)).toEqual([local.key])
    expect(resolved[local.key].draft).toBe('A newer local draft')
  })
  it('derives a deterministic, bounded title from the first question', () => {
    const question = '  Explain   why the two visual regions imply the same conservation law, with a worked example  '
    expect(deriveConversationTitle(question, 48)).toBe('Explain why the two visual regions imply the…')
    expect(deriveConversationTitle(question, 48)).toBe(deriveConversationTitle(question, 48))
  })

  it('sorts dated conversations newest first and keeps undated input stable', () => {
    const conversations: Conversation[] = [
      { id: 1, course: 1, title: 'Undated first' },
      { id: 2, course: 1, title: 'Newest', created_at: '2026-10-15T10:00:00Z' },
      { id: 3, course: 1, title: 'Older', created_at: '2026-10-14T10:00:00Z' },
      { id: 4, course: 1, title: 'Undated second' },
    ]
    expect(sortConversationsNewestFirst(conversations).map(({ id }) => id)).toEqual([2, 3, 1, 4])
  })

  it('isolates late request results to their originating session', () => {
    const sessionA = { ...createLocalChatSession('local:a'), loadRequestId: 1, loading: true }
    const sessionB = { ...createLocalChatSession('local:b'), draft: 'newer edit' }
    const sessions = { [sessionA.key]: sessionA, [sessionB.key]: sessionB }

    const completed = finishSessionRequest(sessions, sessionA.key, 'loadRequestId', 1, (session) => ({
      ...session,
      loading: false,
      messages: [{ id: 1, conversation: 9, role: 'assistant', content: 'A result', citations: [], status: 'complete' }],
    }))

    expect(completed[sessionA.key]?.messages[0]?.content).toBe('A result')
    expect(completed[sessionB.key]).toBe(sessionB)
    expect(completed[sessionB.key]?.draft).toBe('newer edit')
  })

  it('rejects an obsolete A response after A to B to A starts a newer request', () => {
    const sessionA = { ...createLocalChatSession('local:a'), loadRequestId: 2, loading: true }
    const sessionB = createLocalChatSession('local:b')
    const sessions = { [sessionA.key]: sessionA, [sessionB.key]: sessionB }
    const stale = finishSessionRequest(sessions, sessionA.key, 'loadRequestId', 1, (session) => ({ ...session, loading: false }))
    expect(stale).toBe(sessions)
    expect(stale[sessionA.key]?.loading).toBe(true)
  })

  it('attaches a server conversation to a local session without duplicating it', () => {
    const local = { ...createLocalChatSession('local:a'), conversationId: 42, title: 'Initial question' }
    const sessions = { [local.key]: local }
    const reconciled = reconcileConversationSessions(sessions, [{ id: 42, course: 7, title: 'Initial question', created_at: '2026-10-15T10:00:00Z' }])
    expect(Object.keys(reconciled)).toEqual(['local:a'])
    expect(reconciled['local:a']?.createdAt).toBe('2026-10-15T10:00:00Z')

    const edited = updateChatSession(reconciled, 'local:a', { draft: 'second question' })
    expect(edited['local:a']?.draft).toBe('second question')
  })

  it('snapshots attachment arrays, preserves omitted context, and permits explicit region clearing', () => {
    const regions = [7, 8]
    const objectIds = ['graph']
    const initial = attachChatContext(createLocalChatSession('local:a'), { regionIds: regions, videoContext: { label: 'Scene 1', object_ids: objectIds } })
    regions.push(9)
    objectIds.push('axis')
    expect(initial.regionIds).toEqual([7, 8])
    expect(initial.videoContext?.object_ids).toEqual(['graph'])
    const changed = attachChatContext(initial, { regionIds: [] })
    expect(changed.regionIds).toEqual([])
    expect(changed.videoContext).toBe(initial.videoContext)
    expect(changed.contextVersion).toBe(initial.contextVersion + 1)
  })

  it('keeps edits and new attachments made in the originating session during a send', () => {
    const submitted = { ...createLocalChatSession('local:a'), draft: 'First question', regionIds: [1], submitting: true, sendRequestId: 7 }
    const changed = attachChatContext({ ...submitted, draft: 'Next question', draftVersion: 1 }, { regionIds: [2], videoContext: { label: 'New scene' } })
    const completed = completeChatSend(changed, submitted, { id: 9, conversation: 5, role: 'user', content: 'First question', citations: [], status: 'complete' })
    expect(completed.draft).toBe('Next question')
    expect(completed.regionIds).toEqual([2])
    expect(completed.videoContext?.label).toBe('New scene')
    expect(completed.messages[0]?.content).toBe('First question')
    expect(completed.submitting).toBe(false)
  })

  it('clears only the unchanged submitted draft/context and rejects an obsolete send completion', () => {
    const submitted = { ...createLocalChatSession('local:a'), draft: 'First question', regionIds: [1], videoContext: { label: 'Scene' }, submitting: true, sendRequestId: 7 }
    const message = { id: 9, conversation: 5, role: 'user' as const, content: 'First question', citations: [], status: 'complete' as const }
    const completed = completeChatSend(submitted, submitted, message)
    expect(completed.draft).toBe('')
    expect(completed.regionIds).toEqual([])
    expect(completed.videoContext).toBeUndefined()
    const newer = { ...submitted, sendRequestId: 8 }
    const sessions = { [newer.key]: newer }
    expect(finishSessionRequest(sessions, newer.key, 'sendRequestId', 7, (session) => completeChatSend(session, submitted, message))).toBe(sessions)
  })
})


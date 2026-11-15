import { describe, expect, it, vi } from 'vitest'
import { createSessionApi } from './sessionApi'

describe('DEC-003/SES-001 canonical session transport', () => {
  it('accepts readiness only from the canonical ready boolean', async () => {
    const transport = createSessionApi({ get: vi.fn(async () => ({ data: { ready: true } })), post: vi.fn() })
    expect(await transport.scoringReady()).toBe(true)
  })
  it('posts only canonical multipart fields and never calls legacy scoring', async () => {
    const post = vi.fn(async () => ({ data: { decision: 'UNSCORABLE' } }))
    const transport = createSessionApi({ get: vi.fn(), post })
    await transport.assess({ audio: new Blob(['wav'], { type: 'audio/wav' }), sessionId: 'SES-1', attemptId: 'uuid-1', wordId: 'TA_00021', targetWord: 'அம்மா', exerciseVersion: 'ta-core-1.0.0' })
    const [path, form] = post.mock.calls[0]
    expect(path).toBe('/api/v1/word-assessments')
    expect([...form.keys()].sort()).toEqual(['attempt_id', 'audio', 'exercise_version', 'session_id', 'target_word', 'word_id'])
    expect(form.get('target_word')).toBe('அம்மா')
    expect(form.get('exercise_version')).toBe('ta-core-1.0.0')
  })
})

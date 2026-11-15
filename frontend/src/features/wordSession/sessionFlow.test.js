import { describe, expect, it, vi } from 'vitest'
import { createSessionFlow } from './sessionFlow'

const plan = { plan_id: '0000000000000000000000e1', status: 'active', word_ids: ['TA_00021'], vocabulary_version: 'ta-core-1.0.0', session_limits: { max_retries: 2 } }
const active = { session_id: 'SES-1', status: 'active', word_id: 'TA_00021', target_word: 'அம்மா', exercise_version: 'ta-core-1.0.0', attempt_count: 0 }
const next = { ...active, word_id: 'TA_00022', target_word: 'அப்பா', attempt_count: 0 }
const deferred = () => { let resolve; const promise = new Promise((done) => { resolve = done }); return { promise, resolve } }
const api = (overrides = {}) => ({
  assignedPlans: vi.fn(async () => ({ plans: [plan], open_session: null })),
  scoringReady: vi.fn(async () => true),
  start: vi.fn(async () => active), read: vi.fn(async () => active),
  assess: vi.fn(async () => ({ decision: 'PASS', reason_code: 'CALIBRATED_TARGET_MATCH' })),
  pause: vi.fn(async () => ({ ...active, status: 'paused' })),
  resume: vi.fn(async () => active),
  stop: vi.fn(async () => ({ session_id: 'SES-1', status: 'ended' })),
  summary: vi.fn(async () => ({ session_id: 'SES-1', status: 'ended', decisions: { PASS: 0, RETRY: 0, UNSCORABLE: 0 } })),
  ...overrides,
})

describe('SES-001..005 guarded word session', () => {
  it('blocks capture when no authenticated assigned plan is returned', async () => {
    const transport = api({ assignedPlans: async () => ({ plans: [], open_session: null }) })
    const flow = createSessionFlow(transport)
    await flow.load()
    expect(flow.state.phase).toBe('blocked')
    await expect(flow.submit(new Blob(['voice']))).rejects.toThrow('session_not_active')
  })

  it('recovers only the server-owned open session after reload', async () => {
    const transport = api({ assignedPlans: async () => ({ plans: [plan], open_session: active }) })
    const flow = createSessionFlow(transport)
    await flow.load()
    expect(flow.state.snapshot).toEqual(active)
    expect(transport.start).not.toHaveBeenCalled()
  })

  it('blocks capture when local scoring capability is unavailable', async () => {
    const flow = createSessionFlow(api({ scoringReady: async () => false }))
    await flow.load()
    expect(flow.state.phase).toBe('blocked')
    expect(flow.state.reason).toBe('scoring_unavailable')
  })

  it('does not replace a malformed open session with a new client-started session', async () => {
    const transport = api({ assignedPlans: async () => ({ plans: [plan], open_session: { session_id: 'SES-1', status: 'active' } }) })
    const flow = createSessionFlow(transport)
    await flow.load()
    expect(flow.state.phase).toBe('blocked')
    await expect(flow.start(plan.plan_id)).rejects.toThrow('assigned_plan_required')
    expect(transport.start).not.toHaveBeenCalled()
  })

  it('uses the server snapshot target and version, then rereads before advancing', async () => {
    const transport = api({ read: vi.fn().mockResolvedValueOnce(active).mockResolvedValueOnce(next) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    await flow.submit(new Blob(['voice']))
    expect(transport.assess).toHaveBeenCalledWith(expect.objectContaining({
      sessionId: 'SES-1', wordId: 'TA_00021', targetWord: 'அம்மா', exerciseVersion: 'ta-core-1.0.0', attemptId: expect.any(String),
    }))
    expect(flow.state.snapshot.word_id).toBe('TA_00022')
    expect(flow.state.result).toBeNull()
  })

  it('prevents duplicate submission of one capture and preserves its request UUID', async () => {
    const pending = deferred()
    const transport = api({ assess: vi.fn(() => pending.promise) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    const blob = new Blob(['voice'])
    const first = flow.submit(blob)
    const second = flow.submit(blob)
    expect(transport.assess).toHaveBeenCalledTimes(1)
    const id = transport.assess.mock.calls[0][0].attemptId
    expect(id).toMatch(/^[0-9a-f-]{36}$/i)
    pending.resolve({ decision: 'UNSCORABLE', reason_code: 'CALIBRATION_UNAVAILABLE' })
    await Promise.all([first, second])
    expect(transport.assess.mock.calls[0][0].attemptId).toBe(id)
  })

  it.each(['pause', 'stop'])('%s aborts in-flight capture and suppresses a late PASS', async (action) => {
    const pending = deferred()
    const transport = api({ assess: vi.fn(() => pending.promise) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    const attempt = flow.submit(new Blob(['voice']))
    const signal = transport.assess.mock.calls[0][0].signal
    await flow[action]()
    expect(signal.aborted).toBe(true)
    pending.resolve({ decision: 'PASS', response_intent: 'CELEBRATE' })
    await attempt
    expect(flow.state.result).toBeNull()
    expect(flow.state.phase).toBe(action === 'pause' ? 'paused' : 'ended')
  })

  it('does not let a late Pause response revive a completed Stop', async () => {
    const latePause = deferred()
    const transport = api({ pause: vi.fn(() => latePause.promise) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    const pausing = flow.pause()
    await flow.stop()
    latePause.resolve({ ...active, status: 'paused' })
    await pausing
    expect(flow.state.phase).toBe('ended')
    expect(flow.state.snapshot.status).toBe('ended')
  })

  it('derives post-transition phase from the authoritative server status', async () => {
    const transport = api({ pause: vi.fn(async () => ({ ...active, status: 'ended' })) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    await flow.pause()
    expect(flow.state.phase).toBe('ended')
  })

  it('ses004 resumes a voluntary break only from the authoritative server snapshot', async () => {
    const paused = { ...active, status: 'paused', pause_reason: 'user_pause', attempt_count: 1 }
    const transport = api({ pause: vi.fn(async () => paused), resume: vi.fn(async () => ({ ...active, attempt_count: 1 })) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    await flow.pause()
    await flow.resume()
    expect(transport.resume).toHaveBeenCalledWith('SES-1')
    expect(flow.state.phase).toBe('active')
    expect(flow.state.snapshot.attempt_count).toBe(1)
  })

  it('ses004 keeps an early voluntary break paused and never restarts capture', async () => {
    const paused = { ...active, status: 'paused', pause_reason: 'user_pause' }
    const transport = api({ pause: vi.fn(async () => paused), resume: vi.fn(async () => {
      throw { response: { data: { detail: 'completed_break_required' } } }
    }) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    await flow.pause()
    await flow.resume()
    expect(flow.state.phase).toBe('paused')
    expect(flow.state.reason).toBe('completed_break_required')
    expect(flow.state.snapshot.status).toBe('paused')
  })

  it('stops a known session and suppresses a late assessment after route exit', async () => {
    const pending = deferred()
    const transport = api({ assess: vi.fn(() => pending.promise) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    const attempt = flow.submit(new Blob(['voice']))
    const signal = transport.assess.mock.calls[0][0].signal
    await flow.leave()
    expect(signal.aborted).toBe(true)
    expect(transport.stop).toHaveBeenCalledWith('SES-1')
    pending.resolve({ decision: 'PASS' })
    await attempt
    expect(flow.state.result).toBeNull()
  })

  it('does not let an old load overwrite a fresh StrictMode remount load', async () => {
    const old = deferred()
    const transport = api({ assignedPlans: vi.fn().mockImplementationOnce(() => old.promise).mockResolvedValueOnce({ plans: [plan], open_session: active }) })
    const flow = createSessionFlow(transport)
    const first = flow.load()
    const second = flow.load()
    await second
    old.resolve({ plans: [], open_session: null })
    await first
    expect(flow.state.phase).toBe('active')
    expect(flow.state.snapshot).toEqual(active)
    expect(transport.stop).not.toHaveBeenCalled()
  })

  it('best-effort stops a session created after route exit while start was pending', async () => {
    const pending = deferred()
    const transport = api({ start: vi.fn(() => pending.promise) })
    const flow = createSessionFlow(transport)
    await flow.load()
    const starting = flow.start(plan.plan_id)
    await flow.leave()
    pending.resolve(active)
    await starting
    expect(transport.stop).toHaveBeenCalledWith('SES-1')
    expect(flow.state.phase).toBe('ended')
    expect(transport.read).not.toHaveBeenCalled()
  })

  it('does not locally advance on assessment or lesson navigation without a new server snapshot', async () => {
    const pending = deferred()
    const transport = api({ read: vi.fn().mockResolvedValueOnce(active).mockImplementationOnce(() => pending.promise) })
    const flow = createSessionFlow(transport)
    await flow.load(); await flow.start(plan.plan_id)
    const attempt = flow.submit(new Blob(['voice']))
    await Promise.resolve(); await Promise.resolve()
    expect(flow.state.snapshot.word_id).toBe('TA_00021')
    pending.resolve(next); await attempt
    expect(flow.state.snapshot.word_id).toBe('TA_00022')
  })
})

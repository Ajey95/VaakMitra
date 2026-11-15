import { expect, it, vi } from 'vitest'
import { loadVocabulary, probeHealth, readAssignedSession, startAssignedSession, stopAssignedSession, submitAttempt } from './labClient'

it('dec008 preserves the live scoring blocker without fabricating a result', async () => {
  const fetcher = async (url) => new Response(JSON.stringify(
    url === '/health/scoring'
      ? { detail: { ready: false, reasons: ['bundle_config_unavailable'] } }
      : { status: 'ok' },
  ), { status: url === '/health/scoring' ? 503 : 200, headers: { 'Content-Type': 'application/json' } })

  const rows = await probeHealth(fetcher)

  expect(rows.live).toMatchObject({ source: 'live', status: 200 })
  expect(rows.ready).toMatchObject({ source: 'live', status: 200 })
  expect(rows.scoring).toMatchObject({ source: 'live', status: 503, reasons: ['bundle_config_unavailable'] })
})

it('dec016 reports authentication failure rather than inventing vocabulary', async () => {
  let credentialMode
  const fetcher = async (_url, options) => {
    credentialMode = options.credentials
    return new Response('{"detail":"Not authenticated"}', { status: 401, headers: { 'Content-Type': 'application/json' } })
  }

  const response = await loadVocabulary(fetcher)

  expect(credentialMode).toBe('include')
  expect(response).toMatchObject({ source: 'live', status: 401, entries: [] })
})

it('prv002 rejects oversized audio without transporting it', async () => {
  let called = false
  const file = new File([new Uint8Array(8 * 1024 * 1024 + 1)], 'adult.wav', { type: 'audio/wav' })

  await expect(submitAttempt(() => { called = true }, { file })).rejects.toThrow('audio_too_large')
  expect(called).toBe(false)
})

it('au003 reserves room for multipart metadata under the eight MiB request ceiling', async () => {
  let called = false
  const file = new File([new Uint8Array(8 * 1024 * 1024 - 1024)], 'adult.wav', { type: 'audio/wav' })
  await expect(submitAttempt(() => { called = true }, { file })).rejects.toThrow('audio_too_large')
  expect(called).toBe(false)
})

it('dec016 sends exactly the server-listed word and generic WAV filename', async () => {
  let request
  const fetcher = async (url, options) => {
    request = { url, options }
    return new Response(JSON.stringify({ decision: 'UNSCORABLE', reason_code: 'ARTIFACT_MISMATCH', response_intent: 'CAREGIVER_TECHNICAL_HELP', avatar_state: 'BREAK' }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }
  const signal = new AbortController().signal
  const file = new File([new Uint8Array([82, 73, 70, 70, 4, 0, 0, 0, 87, 65, 86, 69])], 'private-person.wav', { type: 'audio/wav' })

  const response = await submitAttempt(fetcher, {
    file, sessionId: 'LAB-1', attemptId: 'ATT-1',
    word: { word_id: 'TA_WORD_0001', canonical_tamil: 'அம்மா' },
    version: 'ta-words-v1.0.0', signal,
  })

  expect(request.url).toBe('/api/v1/word-assessments')
  expect(request.options).toMatchObject({ method: 'POST', credentials: 'include' })
  expect(request.options.signal).toBeInstanceOf(AbortSignal)
  expect([...request.options.body.keys()]).toEqual(['audio', 'session_id', 'attempt_id', 'word_id', 'target_word', 'exercise_version'])
  expect(request.options.body.get('audio').name).toBe('attempt.wav')
  expect(request.options.body.get('target_word')).toBe('அம்மா')
  expect(response).toMatchObject({ source: 'live', status: 200, result: { decision: 'UNSCORABLE' } })
})

it('dec008 does not convert a live HTTP failure into a PASS', async () => {
  const fetcher = async () => new Response('{"detail":"database_unavailable"}', { status: 503, headers: { 'Content-Type': 'application/json' } })
  const file = new File([new Uint8Array([82, 73, 70, 70, 4, 0, 0, 0, 87, 65, 86, 69])], 'adult.wav', { type: 'audio/wav' })

  const response = await submitAttempt(fetcher, {
    file, sessionId: 'LAB-1', attemptId: 'ATT-1',
    word: { word_id: 'TA_WORD_0001', canonical_tamil: 'அம்மா' },
    version: 'ta-words-v1.0.0',
  })

  expect(response).toMatchObject({ source: 'live', status: 503, result: null, error: 'database_unavailable' })
})

it('ux007 gives every live assessment upload a cancellable deadline', async () => {
  let requestSignal
  const fetcher = async (_url, options) => {
    requestSignal = options.signal
    return new Response('{"decision":"UNSCORABLE","reason_code":"MODEL_TIMEOUT"}', { status: 200, headers: { 'Content-Type': 'application/json' } })
  }
  const file = new File([new Uint8Array([82, 73, 70, 70, 4, 0, 0, 0, 87, 65, 86, 69])], 'adult.wav', { type: 'audio/wav' })

  await submitAttempt(fetcher, { file, sessionId: 'LAB-1', attemptId: 'ATT-1',
    word: { word_id: 'TA_WORD_0001', canonical_tamil: 'அம்மா' }, version: 'ta-words-v1.0.0' })

  expect(requestSignal).toBeInstanceOf(AbortSignal)
})

it('ux007 reports an expired assessment deadline without fabricating a result', async () => {
  const deadline = new AbortController()
  const timeout = vi.spyOn(AbortSignal, 'timeout').mockReturnValue(deadline.signal)
  const file = new File([new Uint8Array([82, 73, 70, 70, 4, 0, 0, 0, 87, 65, 86, 69])], 'adult.wav', { type: 'audio/wav' })
  try {
    const pending = submitAttempt((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('timed out', 'AbortError')))
    }), { file, sessionId: 'LAB-1', attemptId: 'ATT-1',
      word: { word_id: 'TA_WORD_0001', canonical_tamil: 'அம்மா' }, version: 'ta-words-v1.0.0' })
    deadline.abort()
    await expect(pending).rejects.toThrow('assessment_timeout')
  } finally {
    timeout.mockRestore()
  }
})

it('dec016 obtains a server-issued assigned word before any audio submission', async () => {
  let request
  const fetcher = async (url, options) => {
    request = { url, options }
    return new Response(JSON.stringify({ session_id: 'SES-owned', word_id: 'TA_WORD_0001',
      target_word: 'அம்மா', exercise_version: 'ta-words-v1.0.0', status: 'active' }),
    { status: 201, headers: { 'Content-Type': 'application/json' } })
  }
  const session = await startAssignedSession(fetcher, '0000000000000000000000e1')
  expect(request.url).toBe('/api/v1/word-sessions')
  expect(request.options).toMatchObject({ method: 'POST', credentials: 'include' })
  expect(JSON.parse(request.options.body)).toEqual({ plan_id: '0000000000000000000000e1' })
  expect(session).toMatchObject({ source: 'live', status: 201, result: { session_id: 'SES-owned', word_id: 'TA_WORD_0001' } })
})

it('dec008 preserves missing session and stop responses without fake scoring', async () => {
  const calls = []
  const fetcher = async (url, options) => {
    calls.push([url, options.method])
    return new Response('{"detail":"word_session_not_found"}', { status: 404, headers: { 'Content-Type': 'application/json' } })
  }
  expect(await readAssignedSession(fetcher, 'SES-missing')).toMatchObject({ source: 'live', status: 404, result: null, error: 'word_session_not_found' })
  expect(await stopAssignedSession(fetcher, 'SES-missing')).toMatchObject({ source: 'live', status: 404, result: null })
  expect(calls).toEqual([['/api/v1/word-sessions/SES-missing', 'GET'], ['/api/v1/word-sessions/SES-missing/stop', 'POST']])
})

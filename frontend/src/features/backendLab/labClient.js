// AU-003 bounds the entire multipart body; reserve room for its fields and boundary.
const MAX_WAV_BYTES = 8 * 1024 * 1024 - 4096

function detailReason(body) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (typeof detail?.reason_code === 'string') return detail.reason_code
  return `HTTP_${body?.status || 'ERROR'}`
}

async function readEndpoint(fetchImpl, path, signal) {
  const timeout = AbortSignal.timeout(8000)
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout
  const started = performance.now()
  try {
    const response = await fetchImpl(path, { method: 'GET', credentials: 'include', signal: combined })
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    return {
      source: 'live', status: response.status, ready: response.ok,
      reasons: Array.isArray(detail?.reasons) ? detail.reasons : response.ok ? [] : [detailReason({ ...body, status: response.status })],
      body, latencyMs: Math.round(performance.now() - started),
    }
  } catch {
    return {
      source: 'live', status: null, ready: false,
      reasons: [timeout.aborted ? 'TIMED_OUT' : signal?.aborted ? 'CANCELLED' : 'NETWORK_ERROR'],
      body: null, latencyMs: Math.round(performance.now() - started),
    }
  }
}

export async function probeHealth(fetchImpl = fetch, signal) {
  const [live, ready, scoring] = await Promise.all([
    readEndpoint(fetchImpl, '/health/live', signal),
    readEndpoint(fetchImpl, '/health/ready', signal),
    readEndpoint(fetchImpl, '/health/scoring', signal),
  ])
  return { live, ready, scoring }
}

export async function loadVocabulary(fetchImpl = fetch, signal) {
  const response = await readEndpoint(fetchImpl, '/api/v1/vocabulary', signal)
  return {
    ...response,
    version: response.ready ? response.body?.vocabulary_version ?? null : null,
    entries: response.ready && Array.isArray(response.body?.entries) ? response.body.entries : [],
  }
}

async function sessionRequest(fetchImpl, url, method, body) {
  const response = await fetchImpl(url, {
    method, credentials: 'include',
    ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(8000),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    return { source: 'live', status: response.status, result: null,
      error: detailReason({ ...payload, status: response.status }) }
  }
  if (typeof payload?.session_id !== 'string' || typeof payload?.status !== 'string') {
    return { source: 'live', status: response.status, result: null, error: 'invalid_session_response' }
  }
  return { source: 'live', status: response.status, result: payload, error: null }
}

export function startAssignedSession(fetchImpl = fetch, planId) {
  if (!/^[0-9a-f]{24}$/i.test(planId ?? '')) throw new Error('invalid_plan_id')
  return sessionRequest(fetchImpl, '/api/v1/word-sessions', 'POST', { plan_id: planId })
}

export function readAssignedSession(fetchImpl = fetch, sessionId) {
  return sessionRequest(fetchImpl, `/api/v1/word-sessions/${encodeURIComponent(sessionId)}`, 'GET')
}

export function stopAssignedSession(fetchImpl = fetch, sessionId) {
  return sessionRequest(fetchImpl, `/api/v1/word-sessions/${encodeURIComponent(sessionId)}/stop`, 'POST')
}

export async function submitAttempt(fetchImpl = fetch, input) {
  const { file, sessionId, attemptId, word, version, signal } = input
  if (!file || file.size === 0) throw new Error('empty_audio')
  if (file.size > MAX_WAV_BYTES) throw new Error('audio_too_large')
  if (!file.name.toLowerCase().endsWith('.wav') || !['audio/wav', 'audio/x-wav', 'audio/wave', ''].includes(file.type)) {
    throw new Error('unsupported_audio_type')
  }
  if (!sessionId || !attemptId || !word?.word_id || !word?.canonical_tamil || !version) {
    throw new Error('missing_server_word_or_session')
  }
  const form = new FormData()
  form.append('audio', file, 'attempt.wav')
  form.append('session_id', sessionId)
  form.append('attempt_id', attemptId)
  form.append('word_id', word.word_id)
  form.append('target_word', word.canonical_tamil)
  form.append('exercise_version', version)
  const timeout = AbortSignal.timeout(20_000)
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout
  let response
  try {
    response = await fetchImpl('/api/v1/word-assessments', {
      method: 'POST', credentials: 'include', body: form, signal: combined,
    })
  } catch (error) {
    if (timeout.aborted) throw new Error('assessment_timeout')
    throw error
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    return { source: 'live', status: response.status, result: null, error: detailReason({ ...body, status: response.status }) }
  }
  if (!['PASS', 'RETRY', 'UNSCORABLE'].includes(body?.decision)) {
    return { source: 'live', status: response.status, result: null, error: 'invalid_response' }
  }
  return { source: 'live', status: response.status, result: body, error: null }
}

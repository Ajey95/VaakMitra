import { assertValidActivity } from './activitySchema'

const DEFAULT_MAX_ATTEMPTS = 3

function countAssistance(assistance, level) {
  if (!level) return assistance
  return { ...assistance, [level]: (assistance[level] || 0) + 1 }
}

function record(state, event) {
  return { ...state, events: [...state.events, event] }
}

function complete(state, event) {
  return record({ ...state, phase: 'complete', completedAt: event.at ?? Date.now() }, event)
}

function advance(state, event) {
  if (state.stepIndex >= state.activity.steps.length - 1) return complete(state, event)
  return record({
    ...state,
    phase: 'prompting',
    stepIndex: state.stepIndex + 1,
    attempt: 0,
    lastResponse: null,
    error: null,
  }, event)
}

export function createSession(activity, now = Date.now()) {
  assertValidActivity(activity)
  return {
    phase: 'intro',
    phaseBeforePause: null,
    activity,
    activityId: activity.id,
    stepIndex: 0,
    attempt: 0,
    hintsUsed: 0,
    effortPoints: 0,
    assistance: {},
    events: [],
    lastResponse: null,
    error: null,
    startedAt: now,
    completedAt: null,
  }
}

export function sessionReducer(state, event) {
  if (!state || !event?.type) return state

  switch (event.type) {
    case 'START':
      return record({ ...state, phase: 'prompting', error: null }, event)
    case 'PROMPT_FINISHED':
      return record({ ...state, phase: 'ready' }, event)
    case 'BEGIN_ATTEMPT':
      return record({ ...state, phase: 'listening', attempt: state.attempt + 1, error: null }, event)
    case 'RESPONSE_CAPTURED':
      return record({ ...state, phase: 'evaluating', lastResponse: event.response ?? null }, event)
    case 'EVALUATION_SUCCEEDED': {
      const step = selectCurrentStep(state)
      return record({
        ...state,
        phase: 'success',
        effortPoints: state.effortPoints + Math.max(0, Number(step?.reward) || 1),
        assistance: countAssistance(state.assistance, event.assistance || 'independent'),
        error: null,
      }, event)
    }
    case 'EVALUATION_RETRY': {
      const maxAttempts = Math.max(1, Number(state.activity.maxAttempts) || DEFAULT_MAX_ATTEMPTS)
      return record({ ...state, phase: state.attempt >= maxAttempts ? 'support' : 'ready' }, event)
    }
    case 'USE_HINT':
      return record({
        ...state,
        phase: 'support',
        hintsUsed: state.hintsUsed + 1,
        assistance: countAssistance(state.assistance, event.assistance || 'visual_prompt'),
      }, event)
    case 'SKIP':
      return advance({ ...state, assistance: countAssistance(state.assistance, 'skipped') }, event)
    case 'NEXT_STEP':
      return advance(state, event)
    case 'PAUSE':
      if (state.phase === 'paused' || state.phase === 'complete') return state
      return record({ ...state, phaseBeforePause: state.phase, phase: 'paused' }, event)
    case 'RESUME':
      if (state.phase !== 'paused') return state
      return record({ ...state, phase: state.phaseBeforePause || 'ready', phaseBeforePause: null }, event)
    case 'COMPLETE':
      return complete(state, event)
    case 'CAPABILITY_ERROR':
      return record({
        ...state,
        phase: 'error',
        error: { capability: event.capability || 'unknown', message: event.message || 'This activity is unavailable.' },
      }, event)
    case 'RESET':
      return createSession(state.activity, event.at ?? Date.now())
    default:
      return state
  }
}

export function selectCurrentStep(state) {
  return state?.activity?.steps?.[state.stepIndex] || null
}

export function selectProgress(state) {
  const total = state?.activity?.steps?.length || 0
  if (!total) return { current: 0, total: 0, percent: 0 }
  if (state.phase === 'complete') return { current: total, total, percent: 100 }
  return {
    current: Math.min(state.stepIndex + 1, total),
    total,
    percent: Math.round((state.stepIndex / total) * 100),
  }
}


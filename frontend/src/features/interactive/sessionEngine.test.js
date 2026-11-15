import { describe, expect, it } from 'vitest'
import {
  createSession,
  selectCurrentStep,
  selectProgress,
  sessionReducer,
} from './sessionEngine'

const activity = {
  id: 'test-activity',
  type: 'quest',
  maxAttempts: 3,
  steps: [
    { id: 'choose', responseMode: 'choice', choices: ['river', 'forest'], reward: 2 },
    { id: 'say', responseMode: 'speech', reward: 3 },
  ],
}

const reduce = (state, type, extra = {}) => sessionReducer(state, { type, at: 2000, ...extra })

describe('interactive session engine', () => {
  it('creates a deterministic serializable session', () => {
    const state = createSession(activity, 1000)
    expect(state).toMatchObject({
      phase: 'intro', activityId: 'test-activity', stepIndex: 0, attempt: 0,
      hintsUsed: 0, effortPoints: 0, startedAt: 1000, completedAt: null,
    })
    expect(state.events).toEqual([])
    expect(selectCurrentStep(state).id).toBe('choose')
    expect(selectProgress(state)).toEqual({ current: 1, total: 2, percent: 0 })
  })

  it('moves through prompting, ready, listening and evaluating', () => {
    let state = createSession(activity, 1000)
    state = reduce(state, 'START')
    expect(state.phase).toBe('prompting')
    state = reduce(state, 'PROMPT_FINISHED')
    expect(state.phase).toBe('ready')
    state = reduce(state, 'BEGIN_ATTEMPT')
    expect(state).toMatchObject({ phase: 'listening', attempt: 1 })
    state = reduce(state, 'RESPONSE_CAPTURED', { response: { choice: 'river' } })
    expect(state.phase).toBe('evaluating')
  })

  it('awards effort and advances after success', () => {
    let state = createSession(activity, 1000)
    state = reduce(reduce(reduce(state, 'START'), 'PROMPT_FINISHED'), 'BEGIN_ATTEMPT')
    state = reduce(state, 'EVALUATION_SUCCEEDED', { assistance: 'independent' })
    expect(state).toMatchObject({ phase: 'success', effortPoints: 2 })
    expect(state.assistance.independent).toBe(1)
    state = reduce(state, 'NEXT_STEP')
    expect(state).toMatchObject({ phase: 'prompting', stepIndex: 1, attempt: 0 })
  })

  it('reveals support on the third unsuccessful attempt without blocking progress', () => {
    let state = createSession(activity, 1000)
    state = reduce(reduce(state, 'START'), 'PROMPT_FINISHED')
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      state = reduce(state, 'BEGIN_ATTEMPT')
      state = reduce(state, 'EVALUATION_RETRY')
      if (attempt < 3) expect(state.phase).toBe('ready')
    }
    expect(state).toMatchObject({ phase: 'support', attempt: 3 })
    state = reduce(state, 'USE_HINT')
    expect(state.hintsUsed).toBe(1)
    state = reduce(state, 'NEXT_STEP')
    expect(state.stepIndex).toBe(1)
  })

  it('records skips as assistance and moves forward', () => {
    let state = createSession(activity, 1000)
    state = reduce(reduce(state, 'START'), 'SKIP')
    expect(state).toMatchObject({ stepIndex: 1, phase: 'prompting' })
    expect(state.assistance.skipped).toBe(1)
  })

  it('pauses and resumes the prior phase', () => {
    let state = reduce(createSession(activity, 1000), 'START')
    state = reduce(state, 'PAUSE')
    expect(state).toMatchObject({ phase: 'paused', phaseBeforePause: 'prompting' })
    state = reduce(state, 'RESUME')
    expect(state.phase).toBe('prompting')
  })

  it('completes the final step and can reset', () => {
    let state = { ...createSession(activity, 1000), stepIndex: 1, phase: 'success', effortPoints: 5 }
    state = reduce(state, 'NEXT_STEP')
    expect(state).toMatchObject({ phase: 'complete', completedAt: 2000 })
    state = reduce(state, 'RESET', { at: 3000 })
    expect(state).toMatchObject({ phase: 'intro', stepIndex: 0, effortPoints: 0, startedAt: 3000 })
  })

  it('turns capability failures into recoverable errors', () => {
    const state = reduce(createSession(activity, 1000), 'CAPABILITY_ERROR', {
      capability: 'microphone', message: 'Microphone unavailable',
    })
    expect(state).toMatchObject({ phase: 'error', error: { capability: 'microphone', message: 'Microphone unavailable' } })
  })
})

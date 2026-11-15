import { describe, expect, it } from 'vitest'
import { createLiveAvatarFlow } from './liveAvatarFlow'

const hint = { phase: 'focus', targetWord: 'அம்மா', chunks: ['அம்', 'மா'], focusIndex: 1 }

describe('DEC-025/DLA-001..006 adult live avatar state machine', () => {
  it('owns the prompt, listen, process, coach, retry and break sequence', () => {
    const flow = createLiveAvatarFlow()
    const started = flow.start('அம்மா')
    expect(started).toMatchObject({ active: true, phase: 'PROMPTING', targetWord: 'அம்மா' })
    const turn = started.turn

    expect(flow.promptComplete(turn).phase).toBe('LISTENING')
    expect(flow.captureComplete(turn).phase).toBe('PROCESSING')
    expect(flow.resolve(turn, 'DEV_TRY_AGAIN', hint)).toMatchObject({ active: true, phase: 'COACH' })
    expect(flow.coachComplete(turn).phase).toBe('RETRY')
    expect(flow.promptComplete(turn).phase).toBe('LISTENING')
    expect(flow.captureComplete(turn).phase).toBe('PROCESSING')
    expect(flow.resolve(turn, 'DEV_TRY_AGAIN', { ...hint, phase: 'break' })).toMatchObject({ active: false, phase: 'BREAK' })
  })

  it('ends a matching turn with praise and an unavailable turn with recapture', () => {
    const flow = createLiveAvatarFlow()
    let turn = flow.start('அம்மா').turn
    flow.promptComplete(turn)
    flow.captureComplete(turn)
    expect(flow.resolve(turn, 'DEV_MATCH', { phase: 'idle' })).toMatchObject({ active: false, phase: 'PRAISE' })

    turn = flow.start('அம்மா').turn
    flow.promptComplete(turn)
    flow.captureComplete(turn)
    expect(flow.resolve(turn, 'DEV_UNAVAILABLE', { phase: 'idle' })).toMatchObject({ active: false, phase: 'ERROR' })
  })

  it('invalidates stale speech callbacks after stop', () => {
    const flow = createLiveAvatarFlow()
    const staleTurn = flow.start('அம்மா').turn
    const stopped = flow.stop()
    expect(stopped).toMatchObject({ active: false, phase: 'IDLE' })
    expect(stopped.turn).not.toBe(staleTurn)
    expect(flow.promptComplete(staleTurn)).toEqual(stopped)
  })
})

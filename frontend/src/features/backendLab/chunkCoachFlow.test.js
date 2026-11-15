import { describe, expect, it } from 'vitest'
import { createChunkCoachFlow } from './chunkCoachFlow'

const hint = { status: 'text_hypothesis', target_word: 'அம்மா', chunks: ['அம்', 'மா'],
  focus_index: 1, focus_position: 'end', basis: 'unvalidated_asr_text_difference' }

describe('DEC-023/DCH-003 adult visual chunk cycle', () => {
  it('walks focus then blend then whole-word retry and stops after two cycles', () => {
    const flow = createChunkCoachFlow()
    expect(flow.start(hint, 'DEV_TRY_AGAIN')).toMatchObject({ phase: 'focus', cycles: 0, focusIndex: 1 })
    expect(flow.advance().phase).toBe('blend')
    expect(flow.advance().phase).toBe('whole_again')
    expect(flow.start(hint, 'DEV_TRY_AGAIN')).toMatchObject({ phase: 'focus', cycles: 1 })
    flow.advance()
    flow.advance()
    expect(flow.start(hint, 'DEV_TRY_AGAIN')).toMatchObject({ phase: 'break', cycles: 2 })
    expect(flow.advance().phase).toBe('break')
  })

  it('allows manual chunk selection without presenting a sound diagnosis', () => {
    const flow = createChunkCoachFlow()
    flow.start({ ...hint, status: 'visual_only', focus_index: null, focus_position: null,
      basis: 'manual_visual_practice' }, 'DEV_UNCERTAIN')
    expect(flow.state.focusIndex).toBe(0)
    expect(flow.select(1)).toMatchObject({ focusIndex: 1, phase: 'focus' })
    expect(flow.state.basis).toBe('manual_visual_practice')
  })

  it('rejects malformed hints and resets target and cycle history', () => {
    const flow = createChunkCoachFlow()
    flow.start(hint, 'DEV_TRY_AGAIN')
    expect(flow.select(8).focusIndex).toBe(1)
    expect(flow.start({ ...hint, chunks: ['அம்', 'wrong'] }).phase).toBe('idle')
    flow.start(hint, 'DEV_TRY_AGAIN')
    flow.advance()
    flow.advance()
    expect(flow.reset()).toMatchObject({ phase: 'idle', cycles: 0, chunks: [] })
  })

  it('does not remediate a development match or unavailable capture', () => {
    const flow = createChunkCoachFlow()
    expect(flow.start(hint, 'DEV_MATCH').phase).toBe('idle')
    expect(flow.start(hint, 'DEV_UNAVAILABLE').phase).toBe('idle')
  })
})

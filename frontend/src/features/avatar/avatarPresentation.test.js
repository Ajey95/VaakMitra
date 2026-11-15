import { describe, expect, it } from 'vitest'
import { presentationForPhase } from './avatarPresentation'

describe('DEC-026/AVT-004 governed avatar presentation', () => {
  const cases = [
    ['IDLE', 'warm', 'rest'],
    ['PROMPTING', 'speaking', 'explain'],
    ['LISTENING', 'attentive', 'listen'],
    ['PROCESSING', 'thinking', 'settle'],
    ['PRAISE', 'joy', 'celebrate'],
    ['COACH', 'encouraging', 'demonstrate'],
    ['RETRY', 'reassuring', 'invite'],
    ['BREAK', 'calm', 'rest'],
    ['ERROR', 'concerned', 'still'],
  ]

  it.each(cases)('%s maps to a fixed expression and gesture', (phase, expression, gesture) => {
    expect(presentationForPhase(phase, 'gentle')).toMatchObject({ expression, gesture })
  })

  it('suppresses body gestures in still mode without changing the session expression', () => {
    expect(presentationForPhase('PRAISE', 'still')).toEqual({ expression: 'joy', gesture: 'still', motion: 'still' })
  })

  it('uses the neutral error presentation for an unknown state', () => {
    expect(presentationForPhase('NOT_A_STATE', 'gentle')).toEqual({ expression: 'concerned', gesture: 'still', motion: 'gentle' })
  })
})


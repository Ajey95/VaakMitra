import { describe, expect, it } from 'vitest'

import { wordAssessmentOutcome } from './outcome'


describe('wordAssessmentOutcome', () => {
  it('celebrates only an explicit PASS without showing a percentage', () => {
    const outcome = wordAssessmentOutcome({ decision: 'PASS', accuracy: 99 })

    expect(outcome.kind).toBe('success')
    expect(outcome.canCelebrate).toBe(true)
    expect(outcome.heading).not.toMatch(/\d+%|accuracy/i)
  })

  it('does not turn a high legacy score into success', () => {
    const outcome = wordAssessmentOutcome({ decision: 'RETRY', accuracy: 99 })

    expect(outcome.kind).toBe('retry')
    expect(outcome.canCelebrate).toBe(false)
    expect(outcome.heading).toContain('once more')
  })

  it('renders model unavailability as neutral and scoreless', () => {
    const outcome = wordAssessmentOutcome({
      decision: 'UNSCORABLE',
      reason_code: 'MODEL_UNAVAILABLE',
      accuracy: null,
    })

    expect(outcome.kind).toBe('unscorable')
    expect(outcome.canCelebrate).toBe(false)
    expect(outcome.showEvidenceBar).toBe(false)
    expect(outcome.heading).toContain('not graded')
  })

  it('treats absent decision as unscorable, not a zero score', () => {
    const outcome = wordAssessmentOutcome({ accuracy: 0 })

    expect(outcome.kind).toBe('unscorable')
    expect(outcome.showEvidenceBar).toBe(false)
  })
})


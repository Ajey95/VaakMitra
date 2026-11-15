import { describe, expect, it } from 'vitest'
import { validateActivity } from '../interactive/activitySchema'
import {
  RIVER_RESCUE_ACTIVITY,
  buildRiverRescueReport,
  evaluateQuestResponse,
  getQuestCopy,
  resolvePathScene,
} from './riverRescueActivity'

describe('River Rescue Voice Quest', () => {
  it('defines five valid deterministic steps with no more than two choices', () => {
    expect(validateActivity(RIVER_RESCUE_ACTIVITY)).toEqual({ valid: true, errors: [] })
    expect(RIVER_RESCUE_ACTIVITY.steps).toHaveLength(5)
    for (const step of RIVER_RESCUE_ACTIVITY.steps) expect(step.choices?.length || 0).toBeLessThanOrEqual(2)
  })

  it('adapts instructions by age band without changing the goal', () => {
    expect(getQuestCopy('call-elephant', 'early').prompt).toBe('Say “aa” to call Kavi!')
    expect(getQuestCopy('call-elephant', 'older').prompt).toContain('clear')
    expect(getQuestCopy('missing', 'middle')).toBeNull()
  })

  it('resolves both opening choices to known story scenes', () => {
    expect(resolvePathScene('forest')).toMatchObject({ path: 'forest', nextStepId: 'call-elephant' })
    expect(resolvePathScene('river')).toMatchObject({ path: 'river', nextStepId: 'call-elephant' })
  })

  it('supports speech, bridge duration, and a three-attempt escape hatch', () => {
    expect(evaluateQuestResponse(RIVER_RESCUE_ACTIVITY.steps[1], { transcript: 'aa' }, 1)).toMatchObject({ success: true })
    expect(evaluateQuestResponse(RIVER_RESCUE_ACTIVITY.steps[1], { transcript: 'no' }, 2)).toMatchObject({ success: false, support: false })
    expect(evaluateQuestResponse(RIVER_RESCUE_ACTIVITY.steps[1], { transcript: 'no' }, 3)).toMatchObject({ success: false, support: true, canAdvance: true })
    expect(evaluateQuestResponse(RIVER_RESCUE_ACTIVITY.steps[3], { durationMs: 1600 }, 1)).toMatchObject({ success: true })
  })

  it('reports only aggregate story progress', () => {
    const report = buildRiverRescueReport({ startedAt: 10, completedAt: 5010, turns: 5, successes: 4, attempts: 7, assistance: { independent: 4, verbal_prompt: 1 } })
    expect(report).toMatchObject({ activity_id: 'river-rescue', activity_type: 'quest', communication_turns: 5, successful_turns: 4, attempts: 7, duration_ms: 5000 })
    expect(JSON.stringify(report)).not.toMatch(/transcript|audio|video|frame|choice_value/i)
  })
})

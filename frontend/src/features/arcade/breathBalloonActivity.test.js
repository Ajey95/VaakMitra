import { describe, expect, it } from 'vitest'
import { validateActivity } from '../interactive/activitySchema'
import { BREATH_BALLOON_ACTIVITY, createBreathBalloonReport } from './breathBalloonActivity'

describe('Breath Balloon activity', () => {
  it('contains three valid, time-limited airflow rounds', () => {
    expect(validateActivity(BREATH_BALLOON_ACTIVITY)).toEqual({ valid: true, errors: [] })
    expect(BREATH_BALLOON_ACTIVITY.steps).toHaveLength(3)
    for (const step of BREATH_BALLOON_ACTIVITY.steps) {
      expect(step.responseMode).toBe('airflow')
      expect(step.timeoutMs).toBe(20_000)
      expect(step.allowSkip).toBe(true)
    }
  })

  it('builds an aggregate-only completion report', () => {
    const report = createBreathBalloonReport({
      startedAt: 1000,
      completedAt: 91000,
      scores: [70, 80, 90],
      attempts: 4,
      assistance: { independent: 2, visual_prompt: 1 },
      effortPoints: 9,
    })
    expect(report).toMatchObject({
      activity_id: 'breath-balloon',
      activity_type: 'arcade',
      communication_turns: 3,
      successful_turns: 3,
      attempts: 4,
      duration_ms: 90_000,
      effort_points: 9,
    })
    expect(JSON.stringify(report)).not.toMatch(/audio|transcript|sample/i)
  })
})

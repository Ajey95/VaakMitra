import { describe, expect, it } from 'vitest'
import {
  ASSISTANCE_LEVELS,
  TALK_TOGETHER_MISSIONS,
  advanceMission,
  buildTalkTogetherReport,
  summarizeAssistance,
} from './talkTogetherActivity'

describe('Talk Together caregiver missions', () => {
  it('defines five media-free missions with one child prompt each', () => {
    expect(TALK_TOGETHER_MISSIONS).toHaveLength(5)
    for (const mission of TALK_TOGETHER_MISSIONS) {
      expect(mission.childPrompt).toBeTruthy()
      expect(mission.childPrompt).not.toBeInstanceOf(Array)
      expect(JSON.stringify(mission)).not.toMatch(/camera|microphone|record|upload/i)
    }
  })

  it('maps the five approved missions to distinct environments and Tamil praise', () => {
    expect(TALK_TOGETHER_MISSIONS.map(({ id, environment }) => [id, environment])).toEqual([
      ['ask-water', 'kitchen'],
      ['choose-snack', 'grocery'],
      ['name-object', 'classroom'],
      ['imitate-turns', 'park'],
      ['say-thanks', 'birthday'],
    ])
    for (const mission of TALK_TOGETHER_MISSIONS) expect(mission.celebrateTa).toMatch(/[\u0B80-\u0BFF]/)
  })

  it('summarizes every assistance level', () => {
    const events = ASSISTANCE_LEVELS.map((assistance) => ({ assistance }))
    expect(summarizeAssistance(events)).toEqual({ independent: 1, verbal_prompt: 1, visual_prompt: 1, modelled: 1, skipped: 1 })
  })

  it('advances deterministically and completes after mission five', () => {
    expect(advanceMission({ missionIndex: 0, complete: false })).toEqual({ missionIndex: 1, complete: false })
    expect(advanceMission({ missionIndex: 4, complete: false })).toEqual({ missionIndex: 4, complete: true })
  })

  it('builds aggregate reporting from caregiver confirmations', () => {
    const events = [
      { assistance: 'independent' }, { assistance: 'verbal_prompt' },
      { assistance: 'visual_prompt' }, { assistance: 'modelled' }, { assistance: 'skipped' },
    ]
    const report = buildTalkTogetherReport({ startedAt: 100, completedAt: 10_100, events })
    expect(report).toMatchObject({ activity_id: 'talk-together', activity_type: 'talk_together', communication_turns: 5, successful_turns: 4, attempts: 5, duration_ms: 10_000 })
    expect(report.assistance_counts).toEqual(summarizeAssistance(events))
  })
})

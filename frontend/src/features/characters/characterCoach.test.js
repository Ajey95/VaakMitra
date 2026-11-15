import { describe, expect, it } from 'vitest'
import {
  PIPPIN_COACH_MISSIONS,
  characterCoachReducer,
  createCoachState,
  getCoachMission,
} from './characterCoach'

function reduce(events) {
  return events.reduce(characterCoachReducer, createCoachState())
}

describe('Pippin character coach', () => {
  it('provides five finite, child-safe missions with picture choices', () => {
    expect(PIPPIN_COACH_MISSIONS).toHaveLength(5)
    for (const mission of PIPPIN_COACH_MISSIONS) {
      expect(mission.prompt.length).toBeGreaterThan(10)
      expect(mission.choices).toHaveLength(2)
      expect(mission.accepted.length).toBeGreaterThan(0)
    }
  })

  it('starts at the first prompt and accepts a matching voice answer', () => {
    const state = reduce([
      { type: 'START' },
      { type: 'BEGIN_LISTENING' },
      { type: 'ANSWER', value: 'Hello Pippin', intent: 'hello', source: 'voice' },
    ])
    expect(state).toMatchObject({ phase: 'success', missionIndex: 0, attempts: 1, lastAssistance: 'independent' })
  })

  it('accepts a picture response without requiring a microphone', () => {
    const state = reduce([
      { type: 'START' },
      { type: 'ANSWER', value: 'Hello', intent: 'hello', source: 'picture' },
    ])
    expect(state).toMatchObject({ phase: 'success', lastAssistance: 'visual_prompt' })
  })

  it('encourages after one mismatch and offers support after two', () => {
    const first = reduce([{ type: 'START' }, { type: 'ANSWER', value: 'unknown', source: 'voice' }])
    expect(first).toMatchObject({ phase: 'encourage', attempts: 1 })
    const second = characterCoachReducer(first, { type: 'ANSWER', value: 'still unknown', source: 'voice' })
    expect(second).toMatchObject({ phase: 'support', attempts: 2 })
  })

  it('lets a child skip without failure language', () => {
    const state = reduce([{ type: 'START' }, { type: 'SKIP' }])
    expect(state).toMatchObject({ phase: 'success', lastAssistance: 'skipped' })
    expect(state.message.toLowerCase()).not.toContain('wrong')
  })

  it('moves through missions and completes after the fifth success', () => {
    let state = createCoachState()
    state = characterCoachReducer(state, { type: 'START' })
    for (let index = 0; index < PIPPIN_COACH_MISSIONS.length; index += 1) {
      const mission = getCoachMission(state)
      state = characterCoachReducer(state, { type: 'ANSWER', value: mission.accepted[0], source: 'picture' })
      state = characterCoachReducer(state, { type: 'NEXT' })
    }
    expect(state).toMatchObject({ phase: 'complete', missionIndex: 4, completedTurns: 5 })
  })

  it('exposes speaking and listening phases for character animation', () => {
    let state = reduce([{ type: 'START' }, { type: 'PROMPT_STARTED' }])
    expect(state.phase).toBe('speaking')
    state = characterCoachReducer(state, { type: 'PROMPT_FINISHED' })
    expect(state.phase).toBe('prompt')
    state = characterCoachReducer(state, { type: 'BEGIN_LISTENING' })
    expect(state.phase).toBe('listening')
  })
})

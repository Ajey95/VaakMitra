import { expect, it } from 'vitest'
import { simulationFor } from './fixtures'

it('dec008 labels each contract example as simulation', () => {
  for (const key of ['pass', 'retry', 'invalid', 'capability']) {
    expect(simulationFor(key).source).toBe('simulation')
  }
})

it('dec008 capability simulation remains scoreless and requests caregiver help', () => {
  expect(simulationFor('capability')).toMatchObject({
    source: 'simulation',
    result: {
      decision: 'UNSCORABLE', reason_code: 'MODEL_UNAVAILABLE',
      word_match_probability: null, response_intent: 'CAREGIVER_TECHNICAL_HELP', avatar_state: 'BREAK',
    },
  })
})

it('dec008 rejects an unknown simulated state', () => {
  expect(() => simulationFor('imaginary')).toThrow('unknown_simulation')
})

import { describe, expect, it } from 'vitest'
import { RESPONSE_MODES, validateActivity } from './activitySchema'

const valid = {
  id: 'river-rescue',
  type: 'quest',
  steps: [
    { id: 'start', responseMode: 'choice', choices: ['river', 'forest'], next: 'finish' },
    { id: 'finish', responseMode: 'speech', target: 'a' },
  ],
}

describe('interactive activity schema', () => {
  it('accepts every supported response mode', () => {
    expect(RESPONSE_MODES).toEqual(new Set(['choice', 'speech', 'airflow', 'mouth_shape', 'caregiver_confirm', 'touch']))
  })

  it('accepts a valid activity', () => {
    expect(validateActivity(valid)).toEqual({ valid: true, errors: [] })
  })

  it('requires a stable id and at least one step', () => {
    const result = validateActivity({ type: 'quest', steps: [] })
    expect(result.valid).toBe(false)
    expect(result.errors).toContain('Activity id is required')
    expect(result.errors).toContain('Activity must contain at least one step')
  })

  it('rejects duplicate ids, unsupported modes and more than two choices', () => {
    const result = validateActivity({
      id: 'bad', type: 'quest', steps: [
        { id: 'same', responseMode: 'magic' },
        { id: 'same', responseMode: 'choice', choices: ['a', 'b', 'c'] },
      ],
    })
    expect(result.errors).toContain('Step ids must be unique')
    expect(result.errors).toContain('Step same has unsupported response mode magic')
    expect(result.errors).toContain('Step same may expose at most two choices')
  })

  it('rejects next-step references that do not exist', () => {
    const result = validateActivity({ ...valid, steps: [{ ...valid.steps[0], next: 'missing' }] })
    expect(result.errors).toContain('Step start references unknown next step missing')
  })
})


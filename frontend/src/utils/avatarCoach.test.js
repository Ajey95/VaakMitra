import { describe, expect, it } from 'vitest'
import { getAvatarCoachMessage, getAvatarCoachMood } from './avatarCoach'

const lesson = { english: 'LA', symbol: 'ல', tip: 'Touch tongue to roof of mouth' }

describe('avatar coach scripts', () => {
  it('creates an encouraging speaking prompt for the evaluation slide', () => {
    expect(getAvatarCoachMessage({ slide: 3, lesson })).toContain('LA')
  })

  it('celebrates a successful evaluation', () => {
    expect(getAvatarCoachMessage({ slide: 3, lesson, outcome: 'success' })).toContain('Great job')
    expect(getAvatarCoachMood({ slide: 3, outcome: 'success' })).toBe('celebrate')
  })
})

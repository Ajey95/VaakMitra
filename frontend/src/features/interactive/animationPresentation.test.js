import { describe, expect, it } from 'vitest'
import {
  TALK_TOGETHER_SCENES,
  getBreathVisualState,
  getEffectProfile,
  getTamilPrompt,
  getTalkTogetherReward,
} from './animationPresentation'

describe('interactive animation presentation', () => {
  it('classifies balloon input without rewarding excessive volume', () => {
    const target = [0.25, 0.7]
    expect(getBreathVisualState({ mode: 'playing', level: 0.1, target })).toBe('too-weak')
    expect(getBreathVisualState({ mode: 'playing', level: 0.45, target })).toBe('steady')
    expect(getBreathVisualState({ mode: 'playing', level: 0.9, target })).toBe('too-strong')
    expect(getBreathVisualState({ mode: 'success', level: 0.45, target })).toBe('success')
    expect(getBreathVisualState({ mode: 'complete', level: 0, target })).toBe('complete')
  })

  it('turns sensory preferences into bounded effect profiles', () => {
    expect(getEffectProfile({ motionLevel: 'full', celebrationLevel: 'full' })).toEqual({ ambient: true, particles: 18, travel: true, durationMs: 4000 })
    expect(getEffectProfile({ motionLevel: 'reduced', celebrationLevel: 'gentle' })).toEqual({ ambient: true, particles: 6, travel: false, durationMs: 1800 })
    expect(getEffectProfile({ motionLevel: 'minimal', celebrationLevel: 'none' })).toEqual({ ambient: false, particles: 0, travel: false, durationMs: 0 })
  })

  it('provides Tamil guidance for every required balloon state', () => {
    for (const state of ['intro', 'too-weak', 'steady', 'too-strong', 'stopped', 'success', 'complete']) {
      expect(getTamilPrompt('breath-balloon', state)).toMatch(/[\u0B80-\u0BFF]/)
    }
  })

  it('maps five Talk Together missions and supportive reward levels', () => {
    expect(TALK_TOGETHER_SCENES.map(({ id }) => id)).toEqual(['ask-water', 'choose-snack', 'name-object', 'imitate-turns', 'say-thanks'])
    expect(getTalkTogetherReward('independent').intensity).toBe('full')
    expect(getTalkTogetherReward('modelled').intensity).toBe('gentle')
    expect(getTalkTogetherReward('skipped').intensity).toBe('none')
  })
})

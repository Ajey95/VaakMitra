import { describe, expect, it } from 'vitest'
import {
  DEFAULT_INTERACTION_PREFERENCES,
  applyCalmMode,
  migrateInteractionPreferences,
  resolveAgeBand,
  resolveInitialPreferences,
} from './preferences'

describe('interaction preferences', () => {
  it.each([
    [4, 'early'], [6, 'early'], [7, 'middle'], [9, 'middle'], [10, 'older'], [12, 'older'],
  ])('maps age %s to %s presentation', (age, expected) => {
    expect(resolveAgeBand(age)).toBe(expected)
  })

  it('uses the middle presentation for missing or invalid ages', () => {
    expect(resolveAgeBand(undefined)).toBe('middle')
    expect(resolveAgeBand('child')).toBe('middle')
    expect(resolveAgeBand(2)).toBe('middle')
    expect(resolveAgeBand(17)).toBe('middle')
  })

  it('migrates saved values while discarding unsupported values and keys', () => {
    const migrated = migrateInteractionPreferences({
      version: 0,
      ageBand: 'older',
      soundEnabled: false,
      motionLevel: 'wild',
      cameraEnabled: true,
      secret: 'discard-me',
    })
    expect(migrated).toEqual({
      ...DEFAULT_INTERACTION_PREFERENCES,
      ageBand: 'older',
      soundEnabled: false,
      cameraEnabled: true,
    })
    expect(migrated).not.toHaveProperty('secret')
  })

  it('persists only allow-listed Pippin voices and defaults invalid values to kitten', () => {
    expect(migrateInteractionPreferences({ pippinVoice: 'gentle' }).pippinVoice).toBe('gentle')
    expect(migrateInteractionPreferences({ pippinVoice: 'celebrity-clone' }).pippinVoice).toBe('kitten')
    expect(DEFAULT_INTERACTION_PREFERENCES.pippinVoice).toBe('kitten')
  })

  it('uses age and reduced-motion system preference when no saved value exists', () => {
    expect(resolveInitialPreferences({ age: 5, prefersReducedMotion: true })).toMatchObject({
      ageBand: 'early',
      motionLevel: 'reduced',
    })
  })

  it('lets an explicit saved setting win over system defaults', () => {
    expect(resolveInitialPreferences({
      age: 5,
      prefersReducedMotion: true,
      saved: { ageBand: 'older', motionLevel: 'full' },
    })).toMatchObject({ ageBand: 'older', motionLevel: 'full' })
  })

  it('calm mode removes nonessential stimulation without disabling all sound', () => {
    expect(applyCalmMode(DEFAULT_INTERACTION_PREFERENCES, true)).toMatchObject({
      motionLevel: 'minimal', celebrationLevel: 'none', spokenPrompts: false, soundEnabled: true,
    })
  })

  it('restores the prior sensory values when calm mode is turned off', () => {
    const original = { ...DEFAULT_INTERACTION_PREFERENCES, motionLevel: 'reduced', celebrationLevel: 'gentle', spokenPrompts: true }
    const calm = applyCalmMode(original, true)
    expect(applyCalmMode(calm, false)).toMatchObject({
      motionLevel: 'reduced', celebrationLevel: 'gentle', spokenPrompts: true,
    })
  })
})

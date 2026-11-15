import { describe, expect, it } from 'vitest'
import {
  DEFAULT_AVATAR_PREFERENCE,
  avatarPreferenceKey,
  loadAvatarPreference,
  normalizeAvatarPreference,
  saveAvatarPreference,
} from './avatarPreference'

function memoryStorage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
  }
}

describe('DEC-026/AVT-002 avatar preference', () => {
  it('falls back when an identifier or raw SVG payload is not catalogued', () => {
    expect(normalizeAvatarPreference({ avatarId: '<svg onload=alert(1)>', paletteId: 'data:image/svg+xml,x', motionLevel: 'wild' }))
      .toEqual(DEFAULT_AVATAR_PREFERENCE)
  })

  it('round-trips a valid versioned preference', () => {
    const storage = memoryStorage()
    const chosen = { schemaVersion: 1, avatarId: 'kavin', paletteId: 'sunrise', motionLevel: 'reduced' }
    saveAvatarPreference(storage, 'child-7', chosen)
    expect(loadAvatarPreference(storage, 'child-7')).toEqual(chosen)
  })

  it('isolates two child profile keys', () => {
    expect(avatarPreferenceKey('child-a')).not.toBe(avatarPreferenceKey('child-b'))
    const storage = memoryStorage()
    saveAvatarPreference(storage, 'child-a', { avatarId: 'nila', paletteId: 'lotus', motionLevel: 'still' })
    expect(loadAvatarPreference(storage, 'child-b')).toEqual(DEFAULT_AVATAR_PREFERENCE)
  })

  it('uses a labelled device preview key only when no profile identifier exists', () => {
    expect(avatarPreferenceKey('')).toBe('vaakmitra:avatar:v1:device-preview')
  })
})

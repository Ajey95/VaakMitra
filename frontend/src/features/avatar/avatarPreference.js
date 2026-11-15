import { AVATAR_CATALOG, AVATAR_MOTION_LEVELS, AVATAR_PALETTES } from './avatarCatalog'

export const DEFAULT_AVATAR_PREFERENCE = Object.freeze({
  schemaVersion: 1,
  avatarId: 'meera',
  paletteId: 'coral-teal',
  motionLevel: 'gentle',
})

const avatarIds = new Set(AVATAR_CATALOG.map(({ id }) => id))
const paletteIds = new Set(AVATAR_PALETTES.map(({ id }) => id))
const motionIds = new Set(AVATAR_MOTION_LEVELS.map(({ id }) => id))

/** DEC-026/AVT-002/003: validate only closed catalogue values. */
export function normalizeAvatarPreference(value) {
  if (!value || typeof value !== 'object' || !avatarIds.has(value.avatarId)) {
    return { ...DEFAULT_AVATAR_PREFERENCE }
  }
  return {
    schemaVersion: 1,
    avatarId: value.avatarId,
    paletteId: paletteIds.has(value.paletteId) ? value.paletteId : DEFAULT_AVATAR_PREFERENCE.paletteId,
    motionLevel: motionIds.has(value.motionLevel) ? value.motionLevel : DEFAULT_AVATAR_PREFERENCE.motionLevel,
  }
}

export function avatarPreferenceKey(childId) {
  const scoped = String(childId ?? '').trim()
  return scoped
    ? `vaakmitra:avatar:v1:child:${encodeURIComponent(scoped)}`
    : 'vaakmitra:avatar:v1:device-preview'
}

export function loadAvatarPreference(storage, childId) {
  try {
    const raw = storage?.getItem?.(avatarPreferenceKey(childId))
    return raw ? normalizeAvatarPreference(JSON.parse(raw)) : { ...DEFAULT_AVATAR_PREFERENCE }
  } catch {
    return { ...DEFAULT_AVATAR_PREFERENCE }
  }
}

export function saveAvatarPreference(storage, childId, value) {
  const normalized = normalizeAvatarPreference(value)
  storage?.setItem?.(avatarPreferenceKey(childId), JSON.stringify(normalized))
  return normalized
}

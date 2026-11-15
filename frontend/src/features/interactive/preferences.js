export const DEFAULT_INTERACTION_PREFERENCES = Object.freeze({
  version: 1,
  ageBand: 'middle',
  soundEnabled: true,
  spokenPrompts: true,
  motionLevel: 'full',
  celebrationLevel: 'gentle',
  contrastMode: 'standard',
  sessionPace: 'guided',
  cameraEnabled: false,
  pippinVoice: 'kitten',
  calmMode: false,
})

const ENUM_VALUES = {
  ageBand: new Set(['early', 'middle', 'older']),
  motionLevel: new Set(['full', 'reduced', 'minimal']),
  celebrationLevel: new Set(['full', 'gentle', 'none']),
  contrastMode: new Set(['standard', 'high']),
  sessionPace: new Set(['guided', 'self']),
  pippinVoice: new Set(['kitten', 'gentle']),
}

const BOOLEAN_KEYS = new Set(['soundEnabled', 'spokenPrompts', 'cameraEnabled', 'calmMode'])

export function resolveAgeBand(age) {
  const value = Number(age)
  if (!Number.isFinite(value) || value < 4 || value > 12) return 'middle'
  if (value <= 6) return 'early'
  if (value <= 9) return 'middle'
  return 'older'
}

export function migrateInteractionPreferences(raw) {
  const next = { ...DEFAULT_INTERACTION_PREFERENCES }
  if (!raw || typeof raw !== 'object') return next

  for (const [key, allowed] of Object.entries(ENUM_VALUES)) {
    if (allowed.has(raw[key])) next[key] = raw[key]
  }
  for (const key of BOOLEAN_KEYS) {
    if (typeof raw[key] === 'boolean') next[key] = raw[key]
  }
  return next
}

export function resolveInitialPreferences({ saved, age, prefersReducedMotion = false } = {}) {
  const defaults = {
    ...DEFAULT_INTERACTION_PREFERENCES,
    ageBand: resolveAgeBand(age),
    motionLevel: prefersReducedMotion ? 'reduced' : DEFAULT_INTERACTION_PREFERENCES.motionLevel,
  }
  return migrateInteractionPreferences({ ...defaults, ...(saved || {}) })
}

export function applyCalmMode(preferences, enabled) {
  const current = migrateInteractionPreferences(preferences)
  if (enabled) {
    return {
      ...current,
      calmMode: true,
      motionLevel: 'minimal',
      celebrationLevel: 'none',
      spokenPrompts: false,
      _calmRestore: {
        motionLevel: current.motionLevel,
        celebrationLevel: current.celebrationLevel,
        spokenPrompts: current.spokenPrompts,
      },
    }
  }

  const restore = preferences?._calmRestore || {}
  const restored = migrateInteractionPreferences({ ...current, ...restore, calmMode: false })
  return restored
}

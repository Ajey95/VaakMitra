export const MOUTH_TARGETS = Object.freeze([
  { id: 'open', label: 'Open', sound: 'ah', minOpen: 0.25, maxOpen: 0.55, minWidth: 0.18, cue: 'Open a little wider', model: 'open' },
  { id: 'long_open', label: 'Long open', sound: 'aa', minOpen: 0.6, maxOpen: 1.2, cue: 'Make a tall open shape', model: 'long-open' },
  { id: 'closed_hum', label: 'Closed hum', sound: 'mmm', minOpen: 0, maxOpen: 0.08, minWidth: 0.18, cue: 'Bring your lips together', model: 'closed' },
  { id: 'lip_pop', label: 'Lip pop', sound: 'pa', minOpen: 0, maxOpen: 0.06, minWidth: 0.13, maxWidth: 0.18, cue: 'Press both lips gently', model: 'pop' },
  { id: 'rounded', label: 'Round lips', sound: 'oo', minOpen: 0.2, maxOpen: 0.45, maxWidth: 0.15, cue: 'Make a small round circle', model: 'round' },
])

export const MOUTH_MIRROR_ACTIVITY = Object.freeze({
  id: 'mouth-mirror',
  type: 'mouth_mirror',
  maxAttempts: 3,
  steps: MOUTH_TARGETS.map((target) => ({
    id: target.id,
    shortLabel: target.label,
    responseMode: 'mouth_shape',
    reward: 2,
  })),
})

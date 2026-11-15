const PRESENTATIONS = Object.freeze({
  IDLE: Object.freeze({ expression: 'warm', gesture: 'rest' }),
  PROMPTING: Object.freeze({ expression: 'speaking', gesture: 'explain' }),
  LISTENING: Object.freeze({ expression: 'attentive', gesture: 'listen' }),
  PROCESSING: Object.freeze({ expression: 'thinking', gesture: 'settle' }),
  PRAISE: Object.freeze({ expression: 'joy', gesture: 'celebrate' }),
  COACH: Object.freeze({ expression: 'encouraging', gesture: 'demonstrate' }),
  RETRY: Object.freeze({ expression: 'reassuring', gesture: 'invite' }),
  BREAK: Object.freeze({ expression: 'calm', gesture: 'rest' }),
  ERROR: Object.freeze({ expression: 'concerned', gesture: 'still' }),
})

/** DEC-026/AVT-004/005: presentation maps state; it never owns policy. */
export function presentationForPhase(phase, motionLevel = 'gentle') {
  const base = PRESENTATIONS[phase] ?? PRESENTATIONS.ERROR
  const motion = ['gentle', 'reduced', 'still'].includes(motionLevel) ? motionLevel : 'gentle'
  return { ...base, gesture: motion === 'still' ? 'still' : base.gesture, motion }
}

export function mouthForAudio(speaking, audioLevel) {
  if (!speaking) return 'neutral'
  const level = Number.isFinite(audioLevel) ? Math.max(0, Math.min(1, audioLevel)) : 0
  if (level >= 0.75) return 'a'
  if (level >= 0.5) return 'o'
  if (level >= 0.25) return 'e'
  return 'm'
}

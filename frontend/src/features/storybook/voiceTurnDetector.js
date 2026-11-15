export const PIPPIN_SILENCE_MS = 3500
export const PIPPIN_MAX_TURN_MS = 15000

const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value))

export function createVoiceTurnDetector({
  silenceMs = PIPPIN_SILENCE_MS,
  minSpeechMs = 180,
  maxTurnMs = PIPPIN_MAX_TURN_MS,
  threshold = 0.1,
} = {}) {
  const requiredSilence = Math.max(250, Number.isFinite(silenceMs) ? silenceMs : PIPPIN_SILENCE_MS)
  const requiredSpeech = Math.max(0, Number.isFinite(minSpeechMs) ? minSpeechMs : 180)
  const turnLimit = Math.max(requiredSpeech + requiredSilence, Number.isFinite(maxTurnMs) ? maxTurnMs : PIPPIN_MAX_TURN_MS)
  const baseThreshold = clamp(Number.isFinite(threshold) ? threshold : 0.1, 0.02, 0.5)
  let state

  const updateThreshold = () => {
    state.effectiveThreshold = Math.max(baseThreshold, Math.min(0.24, state.noiseFloor + 0.045))
  }

  const reset = (now = 0) => {
    state = {
      startedAt: Number.isFinite(now) ? now : 0,
      voiceStartedAt: null,
      lastVoiceAt: null,
      hasSpeech: false,
      announcedSpeech: false,
      completed: false,
      noiseFloor: 0.03,
      effectiveThreshold: baseThreshold,
    }
    updateThreshold()
  }

  const result = (event = 'none', speaking = false) => ({
    event,
    hasSpeech: state.hasSpeech,
    speaking,
  })

  const sample = (rawLevel, rawNow) => {
    if (state.completed) return result()

    const now = Number.isFinite(rawNow) ? Math.max(state.startedAt, rawNow) : state.startedAt
    const level = clamp(Number.isFinite(rawLevel) ? rawLevel : 0, 0, 1)
    if (now - state.startedAt >= turnLimit) {
      state.completed = true
      return result('max-duration')
    }

    if (!state.hasSpeech && state.voiceStartedAt === null && level < state.effectiveThreshold) {
      state.noiseFloor = state.noiseFloor * 0.92 + level * 0.08
      updateThreshold()
    }

    if (level >= state.effectiveThreshold) {
      state.voiceStartedAt ??= now
      state.lastVoiceAt = now
      if (!state.hasSpeech && now - state.voiceStartedAt >= requiredSpeech) state.hasSpeech = true
      if (state.hasSpeech && !state.announcedSpeech) {
        state.announcedSpeech = true
        return result('speech-started', true)
      }
      return result('none', true)
    }

    if (!state.hasSpeech) {
      state.voiceStartedAt = null
      state.lastVoiceAt = null
      return result()
    }

    if (now - state.lastVoiceAt >= requiredSilence) {
      state.completed = true
      return result('turn-complete')
    }
    return result()
  }

  const getState = () => ({ ...state })

  reset()
  return { sample, reset, getState }
}

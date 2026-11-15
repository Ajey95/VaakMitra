export const VOICE_PROFILES = Object.freeze({
  kitten: Object.freeze({ pitch: 1.55, rate: 1.02, guidedRate: 0.94, volume: 0.92 }),
  gentle: Object.freeze({ pitch: 1.16, rate: 0.94, guidedRate: 0.86, volume: 0.88 }),
  kavi: Object.freeze({ pitch: 0.92, rate: 0.88, guidedRate: 0.8, volume: 0.95 }),
  kaviTamil: Object.freeze({ pitch: 1.12, rate: 0.9, guidedRate: 0.82, volume: 0.94 }),
})

export const APPLICATION_VOICE_PROFILE_ID = 'kitten'
const DEFAULT_PROFILE_ID = APPLICATION_VOICE_PROFILE_ID
const FEMALE_VOICE_NAME = /\b(?:female|heera|veena|zira|samantha|aria|jenny|sonia|natasha|karen|moira|tessa|victoria|susan|hazel|serena|sangeeta|pallavi|vani|shruti|aditi|kavya|priya|lekha|ananya)\b/i

function clamp(value, minimum, maximum) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return minimum
  return Math.min(maximum, Math.max(minimum, numeric))
}

export function getVoiceProfile(profileId, { guided = false } = {}) {
  const profile = VOICE_PROFILES[profileId] || VOICE_PROFILES[DEFAULT_PROFILE_ID]
  return {
    pitch: profile.pitch,
    rate: guided ? profile.guidedRate : profile.rate,
    volume: profile.volume,
  }
}

export function selectInstalledVoice(voices, preferredLanguage = 'en-IN', { personality = 'neutral' } = {}) {
  if (!Array.isArray(voices) || voices.length === 0) return null
  const preferred = preferredLanguage.toLowerCase()
  const exact = voices.filter((voice) => voice?.lang?.toLowerCase() === preferred)
  const english = voices.filter((voice) => voice?.lang?.toLowerCase().startsWith('en'))
  const candidates = exact.length > 0 ? exact : english
  if (personality === 'female') {
    const female = candidates.find((voice) => FEMALE_VOICE_NAME.test(voice?.name || ''))
    if (female) return female
  }
  if (candidates.length > 0) return candidates[0]
  return voices.find((voice) => voice?.default) || voices[0] || null
}

export function createCharacterUtterance(text, {
  profileId = DEFAULT_PROFILE_ID,
  guided = false,
  voices = [],
  UtteranceCtor = globalThis.SpeechSynthesisUtterance,
  overrides = {},
  onStart,
  onEnd,
  onError,
  language = 'en-IN',
} = {}) {
  if (typeof UtteranceCtor !== 'function') return null
  const safeText = String(text ?? '').replace(/\s+/g, ' ').trim().slice(0, 320)
  if (!safeText) return null
  const profile = { ...getVoiceProfile(profileId, { guided }), ...overrides }
  const utterance = new UtteranceCtor(safeText)
  utterance.pitch = clamp(profile.pitch, 0.5, 2)
  utterance.rate = clamp(profile.rate, 0.5, 1.5)
  utterance.volume = clamp(profile.volume, 0, 1)
  utterance.lang = language
  const voice = selectInstalledVoice(voices, utterance.lang, {
    personality: profileId === 'kitten' ? 'female' : 'neutral',
  })
  if (voice) utterance.voice = voice
  if (typeof onStart === 'function') utterance.onstart = onStart
  if (typeof onEnd === 'function') utterance.onend = onEnd
  if (typeof onError === 'function') utterance.onerror = onError
  return utterance
}

export function speakCharacter(text, {
  synthesis = globalThis.speechSynthesis,
  UtteranceCtor = globalThis.SpeechSynthesisUtterance,
  enabled = true,
  ...options
} = {}) {
  if (!enabled || !synthesis || typeof synthesis.speak !== 'function') return false
  let voices = []
  try {
    voices = typeof synthesis.getVoices === 'function' ? synthesis.getVoices() : []
  } catch {
    voices = []
  }
  const utterance = createCharacterUtterance(text, { ...options, voices, UtteranceCtor })
  if (!utterance) return false
  try {
    if (typeof synthesis.cancel === 'function') synthesis.cancel()
    synthesis.speak(utterance)
    return true
  } catch (error) {
    options.onError?.(error)
    return false
  }
}

export function watchInstalledVoices(synthesis = globalThis.speechSynthesis, onChange = () => {}) {
  if (!synthesis || typeof onChange !== 'function') return () => {}
  const report = () => {
    let voices = []
    try {
      voices = typeof synthesis.getVoices === 'function' ? synthesis.getVoices() : []
    } catch {
      voices = []
    }
    onChange(Array.isArray(voices) ? voices : [])
  }
  report()
  if (typeof synthesis.addEventListener !== 'function') return () => {}
  synthesis.addEventListener('voiceschanged', report)
  return () => synthesis.removeEventListener?.('voiceschanged', report)
}

export function stopCharacterSpeech(synthesis = globalThis.speechSynthesis) {
  if (typeof synthesis?.cancel === 'function') synthesis.cancel()
}

export function createStoryNarrator({
  scope = globalThis,
  loadAudio,
  speakFallback = speakCharacter,
  stopNative = stopCharacterSpeech,
  nativeTimeoutMs = 8000,
  preferNative = false,
} = {}) {
  let active = null
  let generation = 0
  let nativeTimer = null

  const clearNativeTimer = () => {
    if (nativeTimer !== null) {
      const clearTimer = scope.clearTimeout || globalThis.clearTimeout
      clearTimer(nativeTimer)
      nativeTimer = null
    }
  }

  const releaseRemote = ({ pause = false } = {}) => {
    if (!active) return
    const { audio, url } = active
    active = null
    audio.onended = null
    audio.onerror = null
    if (pause) audio.pause?.()
    scope.URL?.revokeObjectURL?.(url)
  }

  const stop = () => {
    generation += 1
    clearNativeTimer()
    releaseRemote({ pause: true })
    stopNative?.()
  }

  const play = async ({ lineId, text, voiceOptions = {}, onStart, onEnd, onError } = {}) => {
    stop()
    const playGeneration = generation
    const playNative = ({ notifyUnavailable = true } = {}) => {
      let settled = false
      const settle = (callback) => {
        if (settled) return
        settled = true
        clearNativeTimer()
        callback?.()
      }
      nativeTimer = (scope.setTimeout || globalThis.setTimeout)(() => settle(onError), nativeTimeoutMs)
      let spoken = false
      try {
        spoken = speakFallback(text, {
          ...voiceOptions,
          profileId: APPLICATION_VOICE_PROFILE_ID,
          language: 'ta-IN',
          onStart,
          onEnd: () => settle(onEnd),
          onError: () => settle(onError),
        })
      } catch {
        spoken = false
      }
      if (!spoken) {
        settled = true
        clearNativeTimer()
        if (notifyUnavailable) onError?.()
      }
      return spoken
    }

    if (preferNative && playNative({ notifyUnavailable: false })) return 'native'

    if (typeof loadAudio === 'function' && lineId) {
      try {
        const blob = await loadAudio(lineId)
        if (playGeneration !== generation) return 'cancelled'
        if (!(blob instanceof Blob) || blob.size === 0) throw new TypeError('No story audio returned')
        const url = scope.URL.createObjectURL(blob)
        const audio = new scope.Audio(url)
        active = { audio, url }
        audio.onended = () => {
          releaseRemote()
          onEnd?.()
        }
        audio.onerror = () => {
          releaseRemote()
          onError?.()
        }
        onStart?.()
        await audio.play()
        return 'remote'
      } catch {
        releaseRemote()
      }
    }
    if (preferNative) {
      onError?.()
      return 'unavailable'
    }
    return playNative() ? 'native' : 'unavailable'
  }

  return { play, stop }
}

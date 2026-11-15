import { describe, expect, it, vi } from 'vitest'
import {
  APPLICATION_VOICE_PROFILE_ID,
  VOICE_PROFILES,
  createCharacterUtterance,
  createStoryNarrator,
  getVoiceProfile,
  selectInstalledVoice,
  speakCharacter,
  watchInstalledVoices,
} from './characterVoice'

class FakeUtterance {
  constructor(text) {
    this.text = text
  }
}

describe('character voice profiles', () => {
  it('uses the kitten voice as the application-wide spoken profile', () => {
    expect(APPLICATION_VOICE_PROFILE_ID).toBe('kitten')
  })

  it('defines distinct child-safe profiles for Pippin and Kavi', () => {
    expect(VOICE_PROFILES.kitten).toMatchObject({ pitch: 1.55, rate: 1.02, guidedRate: 0.94, volume: 0.92 })
    expect(VOICE_PROFILES.gentle).toMatchObject({ pitch: 1.16, rate: 0.94, guidedRate: 0.86, volume: 0.88 })
    expect(VOICE_PROFILES.kavi).toMatchObject({ pitch: 0.92, rate: 0.88, guidedRate: 0.8, volume: 0.95 })
  })

  it('uses guided pacing and safely falls back from unknown profile ids', () => {
    expect(getVoiceProfile('kitten', { guided: true }).rate).toBe(0.94)
    expect(getVoiceProfile('unknown')).toEqual(getVoiceProfile('kitten'))
  })

  it('selects an Indian English voice before another English or default voice', () => {
    const voices = [
      { name: 'Default', lang: 'fr-FR', default: true },
      { name: 'English', lang: 'en-US', default: false },
      { name: 'Indian English', lang: 'en-IN', default: false },
    ]
    expect(selectInstalledVoice(voices)).toBe(voices[2])
    expect(selectInstalledVoice(voices.slice(0, 2))).toBe(voices[1])
    expect(selectInstalledVoice([voices[0]])).toBe(voices[0])
    expect(selectInstalledVoice([])).toBeNull()
  })

  it('prefers a female Indian English voice for the kitten profile', () => {
    const voices = [
      { name: 'Microsoft Ravi Online', lang: 'en-IN', localService: true },
      { name: 'Microsoft Heera Online', lang: 'en-IN', localService: true },
      { name: 'Samantha', lang: 'en-US', localService: true },
    ]

    expect(selectInstalledVoice(voices, 'en-IN', { personality: 'female' })).toBe(voices[1])
    expect(createCharacterUtterance('Listen to LA', {
      profileId: 'kitten', voices, UtteranceCtor: FakeUtterance,
    }).voice).toBe(voices[1])
  })

  it('prefers an installed Tamil voice for Tamil story narration', () => {
    const voices = [
      { name: 'Default English', lang: 'en-IN', default: true },
      { name: 'Tamil', lang: 'ta-IN', default: false },
    ]
    expect(selectInstalledVoice(voices, 'ta-IN')).toBe(voices[1])
    expect(createCharacterUtterance('கவி வா', {
      profileId: 'kaviTamil', language: 'ta-IN', voices, UtteranceCtor: FakeUtterance,
    })).toMatchObject({ lang: 'ta-IN', voice: voices[1], pitch: 1.12, rate: .9 })
  })

  it('prefers a female Tamil voice for application-wide kitten narration', () => {
    const voices = [
      { name: 'Microsoft Valluvar', lang: 'ta-IN', localService: true },
      { name: 'Pallavi', lang: 'ta-IN', localService: true },
    ]
    const utterance = createCharacterUtterance('Tamil story', {
      profileId: APPLICATION_VOICE_PROFILE_ID,
      language: 'ta-IN',
      voices,
      UtteranceCtor: FakeUtterance,
    })

    expect(utterance).toMatchObject({ voice: voices[1], pitch: 1.55, rate: 1.02 })
  })

  it('creates a bounded utterance without placing user text in a network service', () => {
    const voice = { name: 'Local', lang: 'en-IN', localService: true }
    const utterance = createCharacterUtterance('Hello helper!', {
      profileId: 'kitten',
      guided: true,
      voices: [voice],
      UtteranceCtor: FakeUtterance,
      overrides: { pitch: 9, rate: -3, volume: 4 },
    })
    expect(utterance).toMatchObject({
      text: 'Hello helper!', pitch: 2, rate: 0.5, volume: 1, lang: 'en-IN', voice,
    })
  })

  it('cancels prior speech before speaking and reports when speech is unavailable', () => {
    const synthesis = { cancel: vi.fn(), speak: vi.fn(), getVoices: () => [] }
    expect(speakCharacter('Ready?', { synthesis, UtteranceCtor: FakeUtterance })).toBe(true)
    expect(synthesis.cancel).toHaveBeenCalledOnce()
    expect(synthesis.speak).toHaveBeenCalledOnce()
    expect(speakCharacter('Ready?', { synthesis: null, UtteranceCtor: FakeUtterance })).toBe(false)
  })

  it('reports a speech failure instead of throwing into the training UI', () => {
    const onError = vi.fn()
    const synthesis = {
      cancel: vi.fn(),
      getVoices: () => [],
      speak: () => { throw new Error('voice engine unavailable') },
    }

    expect(speakCharacter('Ready?', { synthesis, UtteranceCtor: FakeUtterance, onError })).toBe(false)
    expect(onError).toHaveBeenCalledOnce()
  })

  it('reports voices that arrive asynchronously and removes its listener', () => {
    const listeners = new Set()
    let voices = []
    const synthesis = {
      getVoices: () => voices,
      addEventListener: vi.fn((name, listener) => listeners.add(listener)),
      removeEventListener: vi.fn((name, listener) => listeners.delete(listener)),
    }
    const onChange = vi.fn()

    const unwatch = watchInstalledVoices(synthesis, onChange)
    voices = [{ name: 'Microsoft Heera', lang: 'en-IN' }]
    listeners.forEach((listener) => listener())
    unwatch()

    expect(onChange).toHaveBeenNthCalledWith(1, [])
    expect(onChange).toHaveBeenLastCalledWith(voices)
    expect(synthesis.removeEventListener).toHaveBeenCalledOnce()
  })

  it('plays only an allow-listed line id through remote audio and cleans its URL', async () => {
    const loadAudio = vi.fn(async () => new Blob(['cute-tamil-voice'], { type: 'audio/mpeg' }))
    const audio = { play: vi.fn(() => Promise.resolve()), pause: vi.fn() }
    const scope = {
      Audio: vi.fn(function Audio() { return audio }),
      URL: { createObjectURL: vi.fn(() => 'blob:story-line'), revokeObjectURL: vi.fn() },
    }
    const narrator = createStoryNarrator({ scope, loadAudio, speakFallback: vi.fn(), stopNative: vi.fn() })

    const mode = await narrator.play({ lineId: 'page_1', text: 'குழந்தையின் உரை அல்ல' })
    audio.onended?.()

    expect(mode).toBe('remote')
    expect(loadAudio).toHaveBeenCalledWith('page_1')
    expect(loadAudio).not.toHaveBeenCalledWith('குழந்தையின் உரை அல்ல')
    expect(audio.play).toHaveBeenCalledOnce()
    expect(scope.URL.revokeObjectURL).toHaveBeenCalledWith('blob:story-line')
  })

  it('falls back to native Tamil speech when the optional provider fails', async () => {
    const speakFallback = vi.fn(() => true)
    const narrator = createStoryNarrator({
      loadAudio: vi.fn(async () => { throw new Error('provider offline') }),
      speakFallback,
      stopNative: vi.fn(),
    })

    const mode = await narrator.play({ lineId: 'page_2', text: 'ஈ என்று சொல்லுங்கள்', voiceOptions: { guided: true } })

    expect(mode).toBe('native')
    expect(speakFallback).toHaveBeenCalledWith('ஈ என்று சொல்லுங்கள்', expect.objectContaining({
      language: 'ta-IN', profileId: 'kitten', guided: true,
    }))
  })

  it('prefers native kitten speech before provider audio for application narration', async () => {
    const loadAudio = vi.fn(async () => new Blob(['provider-voice']))
    const speakFallback = vi.fn(() => true)
    const narrator = createStoryNarrator({
      loadAudio,
      speakFallback,
      stopNative: vi.fn(),
      preferNative: true,
    })

    expect(await narrator.play({ lineId: 'page_1', text: 'Tamil story' })).toBe('native')
    expect(loadAudio).not.toHaveBeenCalled()
    expect(speakFallback).toHaveBeenCalledWith('Tamil story', expect.objectContaining({
      profileId: 'kitten', language: 'ta-IN',
    }))
  })

  it('finishes the narration step when both remote and browser speech are unavailable', async () => {
    const onError = vi.fn()
    const narrator = createStoryNarrator({
      loadAudio: vi.fn(async () => { throw new Error('provider offline') }),
      speakFallback: vi.fn(() => false),
      stopNative: vi.fn(),
    })

    const mode = await narrator.play({ lineId: 'page_1', text: 'அ', onError })

    expect(mode).toBe('unavailable')
    expect(onError).toHaveBeenCalledOnce()
  })

  it('times out a browser voice that never reports completion', async () => {
    vi.useFakeTimers()
    const onError = vi.fn()
    const narrator = createStoryNarrator({
      loadAudio: vi.fn(async () => { throw new Error('provider offline') }),
      speakFallback: vi.fn(() => true),
      stopNative: vi.fn(),
      nativeTimeoutMs: 100,
    })

    expect(await narrator.play({ lineId: 'page_1', text: 'அ', onError })).toBe('native')
    await vi.advanceTimersByTimeAsync(100)

    expect(onError).toHaveBeenCalledOnce()
    vi.useRealTimers()
  })

  it('cancels active remote and native narration', async () => {
    const audio = { play: vi.fn(() => Promise.resolve()), pause: vi.fn() }
    const stopNative = vi.fn()
    const scope = {
      Audio: vi.fn(function Audio() { return audio }),
      URL: { createObjectURL: vi.fn(() => 'blob:story-line'), revokeObjectURL: vi.fn() },
    }
    const narrator = createStoryNarrator({ scope, loadAudio: async () => new Blob(['voice']), stopNative })
    await narrator.play({ lineId: 'page_1', text: 'கதை' })

    narrator.stop()

    expect(audio.pause).toHaveBeenCalledOnce()
    expect(stopNative).toHaveBeenCalled()
    expect(scope.URL.revokeObjectURL).toHaveBeenCalledWith('blob:story-line')
  })
})

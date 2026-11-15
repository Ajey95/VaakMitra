import { describe, expect, it, vi } from 'vitest'
import { createSceneAudioController } from './sceneAudio'

function fixture() {
  const spoken = []
  class Utterance {
    constructor(text) {
      this.text = text
      this.lang = ''
    }
  }
  const oscillator = { connect: vi.fn(), start: vi.fn(), stop: vi.fn(), frequency: { value: 0 } }
  const gain = { connect: vi.fn(), gain: { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() } }
  const context = { currentTime: 1, destination: {}, createOscillator: () => oscillator, createGain: () => gain, close: vi.fn() }
  const scope = {
    SpeechSynthesisUtterance: Utterance,
    speechSynthesis: { cancel: vi.fn(), speak: (utterance) => spoken.push(utterance) },
    AudioContext: class { constructor() { return context } },
  }
  return { scope, spoken, oscillator, context }
}

describe('scene audio controller', () => {
  it('speaks Tamil only when enabled and activated', () => {
    const { scope, spoken } = fixture()
    const audio = createSceneAudioController(scope)
    expect(audio.speakTamil('அருமை!', { enabled: true, activated: false })).toBe(false)
    expect(audio.speakTamil('அருமை!', { enabled: true, activated: true })).toBe(true)
    expect(spoken[0]).toMatchObject({ text: 'அருமை!', lang: 'ta-IN' })
  })

  it('plays bounded success tones and cleans up', () => {
    const { scope, oscillator, context } = fixture()
    const audio = createSceneAudioController(scope)
    expect(audio.playEffect('success', { enabled: true, activated: true })).toBe(true)
    expect(oscillator.start).toHaveBeenCalledOnce()
    expect(oscillator.stop).toHaveBeenCalledOnce()
    audio.stop()
    expect(context.close).toHaveBeenCalledOnce()
  })
})

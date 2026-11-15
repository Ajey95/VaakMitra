import { describe, expect, it, vi } from 'vitest'
import { repeatPhrase, repeatPhraseWithPraise } from './speechRepeat'

describe('repeatPhrase', () => {
  it('speaks the exact cleaned phrase without adding a prefix', () => {
    const speak = vi.fn()
    const scope = {
      speechSynthesis: { cancel: vi.fn(), speak },
      SpeechSynthesisUtterance: class FakeUtterance {
        constructor(text) { this.text = text }
      },
    }

    expect(repeatPhrase('  I am happy  ', { scope })).toBe(true)
    expect(scope.speechSynthesis.cancel).toHaveBeenCalledOnce()
    expect(speak).toHaveBeenCalledOnce()
    expect(speak.mock.calls[0][0].text).toBe('I am happy')
    expect(speak.mock.calls[0][0]).toMatchObject({ pitch: 1.55, rate: 0.94, volume: 0.92 })
  })

  it('uses the best installed female voice for Pippin repeats', () => {
    const voices = [
      { name: 'Microsoft Ravi', lang: 'en-IN', localService: true },
      { name: 'Microsoft Heera', lang: 'en-IN', localService: true },
    ]
    const speak = vi.fn()
    const scope = {
      speechSynthesis: { cancel: vi.fn(), speak, getVoices: () => voices },
      SpeechSynthesisUtterance: class FakeUtterance {
        constructor(text) { this.text = text }
      },
    }

    repeatPhrase('LA', { scope })

    expect(speak.mock.calls[0][0].voice).toBe(voices[1])
  })

  it('does nothing when speech synthesis is unavailable', () => {
    expect(repeatPhrase('hello', { scope: {} })).toBe(false)
    expect(repeatPhrase('   ', { scope: {} })).toBe(false)
  })

  it('reports repeat lifecycle events to the training coach', () => {
    const onStart = vi.fn()
    const onEnd = vi.fn()
    const scope = {
      speechSynthesis: { cancel: vi.fn(), speak: (utterance) => { utterance.onstart(); utterance.onend() } },
      SpeechSynthesisUtterance: class FakeUtterance {
        constructor(text) { this.text = text }
      },
    }

    expect(repeatPhrase('LA', { scope, onStart, onEnd })).toBe(true)
    expect(onStart).toHaveBeenCalledOnce()
    expect(onEnd).toHaveBeenCalledOnce()
  })

  it('repeats only the target sound and then praises with the kitten voice', () => {
    const utterances = []
    const onEnd = vi.fn()
    const scope = {
      speechSynthesis: {
        cancel: vi.fn(),
        getVoices: () => [{ name: 'Microsoft Heera', lang: 'en-IN' }],
        speak: (utterance) => utterances.push(utterance),
      },
      SpeechSynthesisUtterance: class FakeUtterance {
        constructor(text) { this.text = text }
      },
    }

    expect(repeatPhraseWithPraise('  aa  ', { scope, onEnd })).toBe(true)
    expect(utterances.map((utterance) => utterance.text)).toEqual(['aa'])
    utterances[0].onend()
    expect(utterances.map((utterance) => utterance.text)).toEqual(['aa', 'Very good!'])
    expect(utterances[1]).toMatchObject({ pitch: 1.55, voice: { name: 'Microsoft Heera' } })
    utterances[1].onend()
    expect(onEnd).toHaveBeenCalledOnce()
  })
})

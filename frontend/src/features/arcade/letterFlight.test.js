import { describe, expect, it, vi } from 'vitest'
import {
  LETTER_FLIGHT_ROUNDS,
  findNewlyCrossedLetters,
  speakCuteLetterSound,
} from './letterFlight'

describe('balloon letter flight', () => {
  it('provides three ordered letter gates for every round', () => {
    expect(LETTER_FLIGHT_ROUNDS).toHaveLength(3)
    for (const round of LETTER_FLIGHT_ROUNDS) {
      expect(round).toHaveLength(3)
      expect(round.map((gate) => gate.threshold)).toEqual([0.24, 0.5, 0.76])
      expect(round.every((gate) => /^[A-Z]$/.test(gate.letter))).toBe(true)
    }
  })

  it('returns every uncrossed gate passed during one upward movement', () => {
    const crossed = findNewlyCrossedLetters({
      previousLevel: 0.2,
      currentLevel: 0.58,
      obstacles: LETTER_FLIGHT_ROUNDS[0],
      crossedIds: new Set(),
    })
    expect(crossed.map((gate) => gate.letter)).toEqual(['A', 'B'])
  })

  it('does not repeat gates or trigger sounds while the balloon falls', () => {
    const obstacles = LETTER_FLIGHT_ROUNDS[0]
    expect(findNewlyCrossedLetters({
      previousLevel: 0.8, currentLevel: 0.3, obstacles, crossedIds: new Set(),
    })).toEqual([])
    expect(findNewlyCrossedLetters({
      previousLevel: 0.2, currentLevel: 0.58, obstacles, crossedIds: new Set(['round-1-a', 'round-1-b']),
    })).toEqual([])
  })

  it('speaks a gentle, high-pitched phoneme with an available local English voice', () => {
    const speak = vi.fn()
    class Utterance { constructor(text) { this.text = text } }
    const scope = {
      SpeechSynthesisUtterance: Utterance,
      speechSynthesis: {
        cancel: vi.fn(),
        getVoices: () => [
          { name: 'Microsoft Ravi', lang: 'en-IN', localService: true },
          { name: 'Microsoft Heera', lang: 'en-IN', localService: true },
        ],
        speak,
      },
    }

    expect(speakCuteLetterSound(scope, LETTER_FLIGHT_ROUNDS[0][0])).toBe(true)
    const utterance = speak.mock.calls[0][0]
    expect(utterance).toMatchObject({ text: 'ah', lang: 'en-IN', pitch: 1.75, rate: 0.68, volume: 0.92 })
    expect(utterance.voice.name).toBe('Microsoft Heera')
    expect(scope.speechSynthesis.cancel).toHaveBeenCalledOnce()
  })
})

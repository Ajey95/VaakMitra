import { describe, expect, it } from 'vitest'
import { getPippinTargetText, getTrainingPippinState } from './trainingPippin'

const lesson = { english: 'LA', symbol: 'ல', phoneme: 'la' }

describe('training Pippin state', () => {
  it.each([
    [{ slide: 1 }, { phase: 'listen', mood: 'ready' }],
    [{ slide: 2 }, { phase: 'listen', mood: 'repeating' }],
    [{ slide: 3, isRecording: true }, { phase: 'listen', mood: 'listening' }],
    [{ slide: 3, isRepeating: true }, { phase: 'repeat', mood: 'repeating' }],
    [{ slide: 3, isAnalyzing: true }, { phase: 'evaluate', mood: 'preparing' }],
    [{ slide: 3, outcome: 'success' }, { phase: 'complete', mood: 'dance' }],
    [{ slide: 3, outcome: 'retry' }, { phase: 'listen', mood: 'encourage' }],
  ])('maps the session state to the visible Pippin phase', (state, expected) => {
    expect(getTrainingPippinState({ lesson, ...state })).toMatchObject(expected)
  })

  it('keeps the phonetic cue in every training prompt instead of the letter name', () => {
    for (const slide of [1, 2, 3, 4, 5]) {
      expect(getTrainingPippinState({ lesson, slide }).message).toMatch(/lah/i)
    }
    expect(getTrainingPippinState({ lesson: { english: 'A', phoneme: 'a' }, slide: 1 }).message).toContain('Ahhhhh')
    expect(getTrainingPippinState({ lesson: { english: 'AA', phoneme: 'aa' }, slide: 1 }).message).toContain('Aaaaaahhhhh')
  })

  it('builds a clean speakable target without relying on an audio file', () => {
    expect(getPippinTargetText({ phoneme: 'a', english: 'A' })).toBe('Ahhhhh')
    expect(getPippinTargetText({ phoneme: 'aa', english: 'AA' })).toBe('Aaaaaahhhhh')
    expect(getPippinTargetText(lesson)).toBe('lah')
    expect(getPippinTargetText({ phoneme: 'ta' })).toBe('tah')
    expect(getPippinTargetText({ phoneme: 'amma' })).toBe('um-mah')
    expect(getPippinTargetText({ phoneme: 'appa' })).toBe('up-pah')
    expect(getPippinTargetText({ english: '  I am happy  ' })).toBe('I am happy')
    expect(getPippinTargetText({})).toBe('this sound')
  })
})

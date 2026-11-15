import { describe, expect, it } from 'vitest'
import {
  appendLocalHistory,
  getPippinResponse,
  matchPippinIntent,
  resetPippinState,
  toPippinReport,
} from './pippinLogic'

describe('Pippin curated practice logic', () => {
  it.each([
    ['please jump', 'jump'], ['dance Pippin', 'dance'], ['go to sleep', 'sleep'],
    ['eat', 'eat'], ['hello there', 'hello'], ['find the ball', 'ball'],
    ['அம்மா', 'amma'], ['அப்பா', 'appa'], ['அ', 'a'], ['ஆ', 'aa'], ['ல', 'la'],
  ])('matches %s to the curated %s intent', (text, expected) => {
    expect(matchPippinIntent(text)).toBe(expected)
  })

  it('uses a deterministic safe expansion for an unknown single word', () => {
    expect(matchPippinIntent('sunshine')).toBe('repeat')
    expect(getPippinResponse('repeat', 'sunshine')).toBe('Sunshine! What a bright word.')
    expect(getPippinResponse('repeat', 'I will hurt you')).toBe('I heard your voice. Let us try a kind word together.')
  })

  it('caps local-only history at five newest items', () => {
    let history = []
    for (let index = 0; index < 7; index += 1) history = appendLocalHistory(history, { id: index, intent: 'hello' })
    expect(history.map((item) => item.id)).toEqual([6, 5, 4, 3, 2])
  })

  it('excludes arbitrary child transcripts from reporting', () => {
    const report = toPippinReport([{ intent: 'jump', heard: 'private words' }, { intent: 'repeat', heard: 'more private words' }])
    expect(report).toEqual([{ intent: 'jump' }, { intent: 'repeat' }])
    expect(JSON.stringify(report)).not.toContain('private')
  })

  it('resets all ephemeral companion state', () => {
    expect(resetPippinState()).toEqual({ history: [], intentCounts: {}, interactionCount: 0 })
  })
})

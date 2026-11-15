import { describe, expect, it } from 'vitest'
import {
  PIPPIN_MAX_TURN_MS,
  PIPPIN_SILENCE_MS,
  createVoiceTurnDetector,
} from './voiceTurnDetector'

function beginSpeech(detector, startedAt = 1000) {
  expect(detector.sample(0.3, startedAt).event).toBe('none')
  return detector.sample(0.3, startedAt + 180)
}

describe('Pippin voice turn detector', () => {
  it('waits for sustained speech before counting the silence boundary', () => {
    const detector = createVoiceTurnDetector()

    expect(detector.sample(0.02, PIPPIN_SILENCE_MS + 1)).toMatchObject({
      event: 'none',
      hasSpeech: false,
    })
    expect(beginSpeech(detector, 4000)).toMatchObject({
      event: 'speech-started',
      hasSpeech: true,
      speaking: true,
    })
    expect(detector.sample(0.02, 4000 + 180 + PIPPIN_SILENCE_MS - 1).event).toBe('none')
    expect(detector.sample(0.02, 4000 + 180 + PIPPIN_SILENCE_MS).event).toBe('turn-complete')
  })

  it('rejects a short microphone spike as speech', () => {
    const detector = createVoiceTurnDetector()

    expect(detector.sample(0.4, 100).event).toBe('none')
    expect(detector.sample(0.01, 250)).toMatchObject({ event: 'none', hasSpeech: false })
    expect(detector.sample(0.01, 4000)).toMatchObject({ event: 'none', hasSpeech: false })
  })

  it('adapts to bounded room noise and detects a voice above it', () => {
    const detector = createVoiceTurnDetector()
    for (let now = 0; now <= 800; now += 100) detector.sample(0.08, now)

    expect(detector.getState().noiseFloor).toBeGreaterThan(0.03)
    expect(detector.getState().effectiveThreshold).toBeGreaterThan(0.1)
    expect(detector.sample(0.16, 900).event).toBe('none')
    expect(detector.sample(0.16, 1080).event).toBe('speech-started')
  })

  it('restarts the silence clock when speech resumes', () => {
    const detector = createVoiceTurnDetector()
    beginSpeech(detector, 1000)

    expect(detector.sample(0.01, 4400).event).toBe('none')
    expect(detector.sample(0.3, 4500).event).toBe('none')
    expect(detector.sample(0.01, 4500 + PIPPIN_SILENCE_MS - 1).event).toBe('none')
    expect(detector.sample(0.01, 4500 + PIPPIN_SILENCE_MS).event).toBe('turn-complete')
  })

  it('emits completion only once', () => {
    const detector = createVoiceTurnDetector()
    beginSpeech(detector, 1000)

    expect(detector.sample(0, 1180 + PIPPIN_SILENCE_MS).event).toBe('turn-complete')
    expect(detector.sample(0, 1181 + PIPPIN_SILENCE_MS)).toMatchObject({
      event: 'none',
      hasSpeech: true,
    })
  })

  it('caps an open turn and reports whether it contained speech', () => {
    const silent = createVoiceTurnDetector()
    expect(silent.sample(0, PIPPIN_MAX_TURN_MS)).toMatchObject({
      event: 'max-duration',
      hasSpeech: false,
    })

    const spoken = createVoiceTurnDetector()
    beginSpeech(spoken, 1000)
    expect(spoken.sample(0.3, PIPPIN_MAX_TURN_MS)).toMatchObject({
      event: 'max-duration',
      hasSpeech: true,
    })
  })

  it('bounds invalid samples and reset starts a clean turn', () => {
    const detector = createVoiceTurnDetector()
    expect(detector.sample(Number.NaN, 100)).toMatchObject({ event: 'none', hasSpeech: false })
    beginSpeech(detector, 1000)
    detector.reset(9000)

    expect(detector.getState()).toMatchObject({
      startedAt: 9000,
      hasSpeech: false,
      completed: false,
      noiseFloor: 0.03,
    })
    expect(detector.sample(Infinity, 12600).event).toBe('none')
  })
})

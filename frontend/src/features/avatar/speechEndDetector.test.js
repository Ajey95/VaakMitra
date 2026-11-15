import { describe, expect, it } from 'vitest'
import { createSpeechEndDetector } from './speechEndDetector'

describe('DEC-025/DLA-003 bounded speech-end detection', () => {
  it('stops only after speech followed by bounded silence', () => {
    const detector = createSpeechEndDetector({ sampleRate: 16_000 })
    expect(detector.push(new Float32Array(4_000))).toMatchObject({ speechStarted: false, shouldStop: false })
    expect(detector.push(new Float32Array(4_000).fill(0.2))).toMatchObject({ speechStarted: true, shouldStop: false })
    expect(detector.push(new Float32Array(7_000))).toMatchObject({ speechStarted: true, shouldStop: false })
    expect(detector.push(new Float32Array(3_000))).toMatchObject({ speechStarted: true, shouldStop: true })
  })

  it('never treats prolonged silence as a completed word', () => {
    const detector = createSpeechEndDetector({ sampleRate: 16_000 })
    expect(detector.push(new Float32Array(16_000))).toMatchObject({ speechStarted: false, shouldStop: false })
  })
})

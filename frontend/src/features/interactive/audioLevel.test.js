import { describe, expect, it } from 'vitest'
import { createNoiseCalibrator, normalizeAudioLevel, scoreTargetControl } from './audioLevel'

describe('microphone level calibration', () => {
  it('uses a robust two-second background sample', () => {
    const calibrator = createNoiseCalibrator({ durationMs: 2000 })
    calibrator.add(0.08, 0)
    calibrator.add(0.1, 500)
    calibrator.add(0.09, 1000)
    calibrator.add(0.95, 1500) // a bump must not dominate background noise
    expect(calibrator.add(0.11, 2000)).toMatchObject({ complete: true })
    expect(calibrator.result()).toBeCloseTo(0.095, 3)
  })

  it('normalizes microphone input above the local floor and clamps it', () => {
    expect(normalizeAudioLevel(0.1, 0.1)).toBe(0)
    expect(normalizeAudioLevel(0.55, 0.1)).toBeCloseTo(0.5)
    expect(normalizeAudioLevel(2, 0.1)).toBe(1)
    expect(normalizeAudioLevel(-1, 0.1)).toBe(0)
  })

  it('scores time in the target zone and does not reward extreme peaks', () => {
    expect(scoreTargetControl([0.3, 0.4, 0.6, 0.95], 0.25, 0.7)).toBe(75)
    expect(scoreTargetControl([0.95, 1, 0.99], 0.25, 0.7)).toBe(0)
    expect(scoreTargetControl([], 0.25, 0.7)).toBe(0)
  })
})

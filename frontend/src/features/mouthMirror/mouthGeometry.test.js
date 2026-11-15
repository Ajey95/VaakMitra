import { describe, expect, it } from 'vitest'
import { classifyMouthTarget, createHoldTracker, measureMouthGeometry } from './mouthGeometry'
import { MOUTH_TARGETS } from './targets'

function landmarks({ left = [0.4, 0.5], right = [0.6, 0.5], upper = [0.5, 0.47], lower = [0.5, 0.53] } = {}) {
  const points = Array.from({ length: 292 }, () => ({ x: 0, y: 0 }))
  points[61] = { x: left[0], y: left[1] }
  points[291] = { x: right[0], y: right[1] }
  points[13] = { x: upper[0], y: upper[1] }
  points[14] = { x: lower[0], y: lower[1] }
  return points
}

describe('privacy-safe mouth geometry', () => {
  it('returns only mouth dimensions and opening ratio', () => {
    expect(measureMouthGeometry(landmarks())).toEqual({ mouthWidth: 0.2, mouthHeight: 0.06, mouthOpenRatio: 0.3 })
  })

  it('returns null for invalid or incomplete landmarks', () => {
    expect(measureMouthGeometry(null)).toBeNull()
    expect(measureMouthGeometry([])).toBeNull()
    expect(measureMouthGeometry(Array(20))).toBeNull()
  })

  it.each([
    ['open', { mouthWidth: 0.2, mouthHeight: 0.08, mouthOpenRatio: 0.4 }],
    ['long_open', { mouthWidth: 0.16, mouthHeight: 0.12, mouthOpenRatio: 0.75 }],
    ['closed_hum', { mouthWidth: 0.2, mouthHeight: 0.01, mouthOpenRatio: 0.05 }],
    ['lip_pop', { mouthWidth: 0.16, mouthHeight: 0.005, mouthOpenRatio: 0.03 }],
    ['rounded', { mouthWidth: 0.12, mouthHeight: 0.04, mouthOpenRatio: 0.33 }],
  ])('classifies the %s target from geometry only', (id, geometry) => {
    expect(classifyMouthTarget(geometry, MOUTH_TARGETS.find((target) => target.id === id))).toMatchObject({ matched: true, cue: 'Hold it' })
  })

  it('requires a continuous 600 millisecond hold', () => {
    const tracker = createHoldTracker(600)
    expect(tracker.update(true, 250)).toMatchObject({ complete: false, heldMs: 250 })
    expect(tracker.update(false, 100)).toMatchObject({ complete: false, heldMs: 0 })
    expect(tracker.update(true, 300)).toMatchObject({ complete: false, heldMs: 300 })
    expect(tracker.update(true, 300)).toMatchObject({ complete: true, heldMs: 600 })
  })
})

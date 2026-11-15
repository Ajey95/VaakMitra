import { describe, expect, it } from 'vitest'
import { PLAY_DESTINATIONS } from './activityCatalog'

describe('Play & Practice catalog', () => {
  it('exposes the five child activities and caregiver settings destination', () => {
    expect(PLAY_DESTINATIONS).toHaveLength(6)
    expect(PLAY_DESTINATIONS.map((item) => item.path)).toEqual([
      '/play/arcade/breath-balloon',
      '/play/quest/river-rescue',
      '/play/mouth-mirror',
      '/play/pippin',
      '/play/together',
      '/play/settings',
    ])
  })

  it('keeps descriptions short and labels every media capability', () => {
    for (const item of PLAY_DESTINATIONS) {
      expect(item.title.length).toBeLessThanOrEqual(24)
      expect(item.description.length).toBeLessThanOrEqual(90)
      expect(['microphone', 'camera', 'none']).toContain(item.capability)
    }
  })
})

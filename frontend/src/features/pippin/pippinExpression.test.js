import { describe, expect, it } from 'vitest'
import { getPippinExpression } from './pippinExpression'

describe('Pippin expression choreography', () => {
  it('keeps idle Pippin warmly alive without demanding attention', () => {
    expect(getPippinExpression('idle', 0)).toEqual({
      face: 'smile',
      blink: 'gentle',
      ears: 'relaxed',
      tail: 'gentle',
      body: 'breathing',
      paws: 'still',
    })
  })

  it('points the ears forward and quiets the body while listening', () => {
    expect(getPippinExpression('listening', 0.2)).toMatchObject({
      face: 'focused', ears: 'forward', tail: 'slow', body: 'listening', paws: 'still',
    })
  })

  it('coordinates happy tail, mouth, ears, and paws for active moods', () => {
    expect(getPippinExpression('repeating', 0.4)).toMatchObject({ face: 'speaking', ears: 'perked', tail: 'happy' })
    expect(getPippinExpression('sing', 0)).toMatchObject({ face: 'speaking', ears: 'perked', tail: 'happy', paws: 'bounce' })
    expect(getPippinExpression('dance', 0)).toMatchObject({ face: 'wide-smile', tail: 'fast', paws: 'dance' })
  })

  it('uses the live audio level to animate speech even before the mood changes', () => {
    expect(getPippinExpression('ready', 0.18).face).toBe('speaking')
  })
})

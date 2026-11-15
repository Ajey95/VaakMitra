import { describe, expect, it, vi } from 'vitest'
import { supportsWebGL } from './webglSupport'

describe('WebGL support detection', () => {
  it('returns true when a WebGL context can be created', () => {
    const canvas = { getContext: vi.fn((name) => (name === 'webgl2' ? { renderer: 'test' } : null)) }
    const documentRef = { createElement: vi.fn(() => canvas) }
    expect(supportsWebGL({ documentRef })).toBe(true)
  })

  it('uses the accessible fallback when forced or context creation fails', () => {
    const documentRef = { createElement: () => ({ getContext: () => null }) }
    expect(supportsWebGL({ documentRef })).toBe(false)
    expect(supportsWebGL({ documentRef, forceFallback: true })).toBe(false)
    expect(supportsWebGL({ documentRef: null })).toBe(false)
  })

  it('handles browser security or driver exceptions without crashing', () => {
    const documentRef = { createElement: () => { throw new Error('blocked') } }
    expect(supportsWebGL({ documentRef })).toBe(false)
  })
})

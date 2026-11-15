import { describe, expect, it, vi } from 'vitest'
import { buildKittenEchoReport, createKittenEcho } from './kittenEcho'

function createWebAudioScope({ decodeFails = false, autoEnd = true } = {}) {
  const connections = []
  const sources = []
  const filters = []
  const compressors = []
  const contexts = []
  let nextFrame = 0
  class AudioContext {
    constructor() {
      this.destination = { type: 'destination' }
      this.closed = false
      contexts.push(this)
    }
    decodeAudioData() {
      return decodeFails ? Promise.reject(new Error('decode failed')) : Promise.resolve({ duration: 0.2 })
    }
    createBufferSource() {
      const source = {
        playbackRate: { value: 1 },
        connect(node) { connections.push(['source', node.type]); return node },
        disconnect: vi.fn(),
        stop: vi.fn(),
        start() { if (autoEnd) queueMicrotask(() => source.onended?.()) },
      }
      sources.push(source)
      return source
    }
    createGain() {
      return { type: 'gain', gain: { value: 1 }, connect(node) { connections.push(['gain', node.type]); return node }, disconnect: vi.fn() }
    }
    createBiquadFilter() {
      const filter = {
        type: 'lowpass',
        frequency: { value: 0 },
        gain: { value: 0 },
        connect(node) { connections.push([filter.type, node.type]); return node },
        disconnect: vi.fn(),
      }
      filters.push(filter)
      return filter
    }
    createDynamicsCompressor() {
      const compressor = {
        type: 'compressor',
        connect(node) { connections.push(['compressor', node.type]); return node },
        disconnect: vi.fn(),
      }
      compressors.push(compressor)
      return compressor
    }
    createAnalyser() {
      return {
        type: 'analyser',
        fftSize: 0,
        connect(node) { connections.push(['analyser', node.type]); return node },
        disconnect: vi.fn(),
        getByteTimeDomainData(array) { array.fill(150) },
      }
    }
    close() { this.closed = true; return Promise.resolve() }
  }
  const fallbackAudio = {
    playbackRate: 1,
    play: vi.fn(() => { queueMicrotask(() => fallbackAudio.onended?.()); return Promise.resolve() }),
    pause: vi.fn(),
  }
  const Audio = vi.fn(function Audio(url) { fallbackAudio.src = url; return fallbackAudio })
  const scope = {
    AudioContext,
    Audio,
    URL: { createObjectURL: vi.fn(() => 'blob:local-echo'), revokeObjectURL: vi.fn() },
    requestAnimationFrame: vi.fn(() => ++nextFrame),
    cancelAnimationFrame: vi.fn(),
    fetch: vi.fn(() => { throw new Error('network must not be used') }),
    XMLHttpRequest: class { constructor() { throw new Error('XHR must not be used') } },
  }
  return { scope, connections, sources, filters, compressors, contexts, fallbackAudio }
}

describe('local kitten echo', () => {
  it('builds only the aggregate fields accepted by private reporting', () => {
    const report = buildKittenEchoReport({ startedAt: 100, completedAt: 2100, repeatCount: 3 })
    expect(report).toEqual({
      activity_id: 'pippin-local-echo',
      activity_type: 'pippin',
      started_at: new Date(100).toISOString(),
      completed_at: new Date(2100).toISOString(),
      communication_turns: 3,
      successful_turns: 3,
      attempts: 3,
      assistance_counts: { independent: 3, verbal_prompt: 0, visual_prompt: 0, modelled: 0, skipped: 0 },
      duration_ms: 2000,
      effort_points: 6,
    })
    expect(JSON.stringify(report)).not.toMatch(/transcript|audio|blob|utterance/i)
  })

  it('decodes and plays the recording locally at a cute kitten rate', async () => {
    const fixture = createWebAudioScope()
    const echo = createKittenEcho({ scope: fixture.scope })

    await echo.play(new Blob(['child-voice'], { type: 'audio/webm' }))

    expect(fixture.sources).toHaveLength(1)
    expect(fixture.sources[0].playbackRate.value).toBe(1.24)
    expect(fixture.filters[0]).toMatchObject({
      type: 'highshelf',
      frequency: { value: 1800 },
      gain: { value: 4 },
    })
    expect(fixture.connections).toEqual([
      ['source', 'highshelf'],
      ['highshelf', 'compressor'],
      ['compressor', 'analyser'],
      ['analyser', 'gain'],
      ['gain', 'destination'],
    ])
    expect(fixture.scope.fetch).not.toHaveBeenCalled()
  })

  it('reports a bounded local audio level through the analyser', async () => {
    const fixture = createWebAudioScope()
    let animationCallback
    fixture.scope.requestAnimationFrame = vi.fn((callback) => { animationCallback = callback; return 7 })
    const onLevel = vi.fn()
    const echo = createKittenEcho({ scope: fixture.scope, onLevel })

    const playing = echo.play(new Blob(['voice']))
    await vi.waitFor(() => expect(fixture.sources).toHaveLength(1))
    animationCallback?.()
    await playing

    expect(onLevel).toHaveBeenCalledWith(expect.any(Number))
    expect(onLevel.mock.calls[0][0]).toBeGreaterThanOrEqual(0)
    expect(onLevel.mock.calls[0][0]).toBeLessThanOrEqual(1)
  })

  it('falls back to a local Audio element when Web Audio decoding fails', async () => {
    const fixture = createWebAudioScope({ decodeFails: true })
    const echo = createKittenEcho({ scope: fixture.scope })

    await echo.play(new Blob(['voice']))

    expect(fixture.scope.URL.createObjectURL).toHaveBeenCalledOnce()
    expect(fixture.scope.Audio).toHaveBeenCalledWith('blob:local-echo')
    expect(fixture.fallbackAudio.playbackRate).toBe(1.24)
    expect(fixture.fallbackAudio.play).toHaveBeenCalledOnce()
    expect(fixture.scope.URL.revokeObjectURL).toHaveBeenCalledWith('blob:local-echo')
  })

  it('stops playback and disposes every local resource idempotently', async () => {
    const fixture = createWebAudioScope({ autoEnd: false })
    const echo = createKittenEcho({ scope: fixture.scope })
    const playing = echo.play(new Blob(['voice']))
    await vi.waitFor(() => expect(fixture.sources).toHaveLength(1))

    echo.stop()
    await playing
    await echo.dispose()
    await echo.dispose()

    expect(fixture.sources[0].stop).toHaveBeenCalled()
    expect(fixture.filters[0].disconnect).toHaveBeenCalled()
    expect(fixture.compressors[0].disconnect).toHaveBeenCalled()
    expect(fixture.scope.cancelAnimationFrame).toHaveBeenCalled()
    expect(fixture.contexts[0].closed).toBe(true)
  })
})

export const KITTEN_RATE = 1.24

export function buildKittenEchoReport({ startedAt, completedAt = Date.now(), repeatCount = 0 }) {
  const start = Number.isFinite(startedAt) ? startedAt : completedAt
  const finish = Math.max(start, completedAt)
  const turns = Math.min(100, Math.max(0, Math.trunc(repeatCount)))
  return {
    activity_id: 'pippin-local-echo',
    activity_type: 'pippin',
    started_at: new Date(start).toISOString(),
    completed_at: new Date(finish).toISOString(),
    communication_turns: turns,
    successful_turns: turns,
    attempts: turns,
    assistance_counts: { independent: turns, verbal_prompt: 0, visual_prompt: 0, modelled: 0, skipped: 0 },
    duration_ms: Math.min(3_600_000, finish - start),
    effort_points: turns * 2,
  }
}

export function createKittenEcho({ scope = globalThis, onLevel = () => {} } = {}) {
  let context = null
  let current = null
  let disposed = false

  const finishCurrent = () => {
    if (!current) return
    const playback = current
    current = null
    if (playback.frame) scope.cancelAnimationFrame?.(playback.frame)
    playback.source?.disconnect?.()
    playback.filter?.disconnect?.()
    playback.compressor?.disconnect?.()
    playback.analyser?.disconnect?.()
    playback.gain?.disconnect?.()
    if (playback.audio) {
      playback.audio.onended = null
      playback.audio.onerror = null
    }
    if (playback.url) scope.URL?.revokeObjectURL?.(playback.url)
    onLevel(0)
    playback.resolve?.()
  }

  const stop = () => {
    if (!current) return
    try { current.source?.stop?.() } catch { /* already stopped */ }
    try { current.audio?.pause?.() } catch { /* already paused */ }
    finishCurrent()
  }

  const playWithAudioElement = (blob) => new Promise((resolve) => {
    const url = scope.URL.createObjectURL(blob)
    const audio = new scope.Audio(url)
    audio.playbackRate = KITTEN_RATE
    current = { audio, url, resolve }
    audio.onended = finishCurrent
    audio.onerror = finishCurrent
    Promise.resolve(audio.play()).catch(finishCurrent)
  })

  const play = async (blob) => {
    if (disposed) throw new Error('Kitten echo has been disposed')
    if (!(blob instanceof Blob) || blob.size === 0) throw new TypeError('A non-empty audio Blob is required')
    stop()

    const AudioContextCtor = scope.AudioContext || scope.webkitAudioContext
    if (!AudioContextCtor) return playWithAudioElement(blob)
    try {
      context ||= new AudioContextCtor()
      const buffer = await context.decodeAudioData(await blob.arrayBuffer())
      if (disposed) return undefined
      const source = context.createBufferSource()
      const filter = context.createBiquadFilter()
      const compressor = context.createDynamicsCompressor()
      const analyser = context.createAnalyser()
      const gain = context.createGain()
      filter.type = 'highshelf'
      filter.frequency.value = 1800
      filter.gain.value = 4
      analyser.fftSize = 256
      gain.gain.value = 0.9
      source.buffer = buffer
      source.playbackRate.value = KITTEN_RATE
      source.connect(filter)
      filter.connect(compressor)
      compressor.connect(analyser)
      analyser.connect(gain)
      gain.connect(context.destination)

      return await new Promise((resolve) => {
        const samples = new Uint8Array(analyser.fftSize)
        current = { source, filter, compressor, analyser, gain, frame: 0, resolve }
        const sampleLevel = () => {
          if (!current || current.source !== source) return
          analyser.getByteTimeDomainData(samples)
          let energy = 0
          for (const sample of samples) energy += ((sample - 128) / 128) ** 2
          onLevel(Math.min(1, Math.sqrt(energy / samples.length) * 2.4))
          current.frame = scope.requestAnimationFrame?.(sampleLevel) || 0
        }
        current.frame = scope.requestAnimationFrame?.(sampleLevel) || 0
        source.onended = finishCurrent
        source.start()
      })
    } catch {
      if (disposed) return undefined
      return playWithAudioElement(blob)
    }
  }

  const dispose = async () => {
    if (disposed) return
    disposed = true
    stop()
    const activeContext = context
    context = null
    if (activeContext?.close) await activeContext.close().catch(() => {})
  }

  return { play, stop, dispose }
}

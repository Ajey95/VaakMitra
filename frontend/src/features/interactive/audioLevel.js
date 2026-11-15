export function createNoiseCalibrator({ durationMs = 2000 } = {}) {
  const samples = []
  let complete = false

  return {
    add(value, elapsedMs = 0) {
      if (Number.isFinite(value)) samples.push(Math.max(0, Math.min(1, value)))
      if (elapsedMs >= durationMs) complete = true
      return { complete, sampleCount: samples.length }
    },
    result() {
      if (!samples.length) return 0.05
      const ordered = [...samples].sort((a, b) => a - b)
      // Ignore the noisiest 20%; a cough or chair bump is not the room floor.
      const stable = ordered.slice(0, Math.max(1, Math.ceil(ordered.length * 0.8)))
      const middle = Math.floor(stable.length / 2)
      return stable.length % 2
        ? stable[middle]
        : (stable[middle - 1] + stable[middle]) / 2
    },
    reset() {
      samples.length = 0
      complete = false
    },
  }
}

export function normalizeAudioLevel(raw, noiseFloor = 0) {
  const safeRaw = Number.isFinite(raw) ? raw : 0
  const safeFloor = Number.isFinite(noiseFloor) ? Math.max(0, Math.min(0.95, noiseFloor)) : 0
  return Math.max(0, Math.min(1, (safeRaw - safeFloor) / Math.max(0.05, 1 - safeFloor)))
}

export function inTargetZone(level, min = 0.25, max = 0.7) {
  return Number.isFinite(level) && level >= min && level <= max
}

export function scoreTargetControl(samples, min = 0.25, max = 0.7) {
  if (!Array.isArray(samples) || samples.length === 0) return 0
  const valid = samples.filter(Number.isFinite)
  if (!valid.length) return 0
  return Math.round(valid.filter((value) => inTargetZone(value, min, max)).length / valid.length * 100)
}

export function readAnalyserLevel(analyser) {
  if (!analyser?.frequencyBinCount) return 0
  const values = new Uint8Array(analyser.frequencyBinCount)
  analyser.getByteFrequencyData(values)
  return values.reduce((sum, value) => sum + value, 0) / values.length / 255
}

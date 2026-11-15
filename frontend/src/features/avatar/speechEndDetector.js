function rms(samples) {
  if (!samples?.length) return 0
  let energy = 0
  for (let index = 0; index < samples.length; index += 1) energy += samples[index] * samples[index]
  return Math.sqrt(energy / samples.length)
}

/** DLA-003: a local capture convenience only; ONNX VAD remains the assessment gate. */
export function createSpeechEndDetector({ sampleRate, threshold = 0.018, minimumSpeechMs = 180, trailingSilenceMs = 600 }) {
  const minimumSpeechSamples = sampleRate * minimumSpeechMs / 1000
  const trailingSilenceSamples = sampleRate * trailingSilenceMs / 1000
  let speechSamples = 0
  let silenceSamples = 0

  return {
    push(samples) {
      const level = rms(samples)
      if (level >= threshold) {
        speechSamples += samples.length
        silenceSamples = 0
      } else if (speechSamples >= minimumSpeechSamples) silenceSamples += samples.length
      const speechStarted = speechSamples >= minimumSpeechSamples
      return { level, speechStarted, shouldStop: speechStarted && silenceSamples >= trailingSilenceSamples }
    },
  }
}

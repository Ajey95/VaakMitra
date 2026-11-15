const EFFECT_FREQUENCIES = Object.freeze({
  success: 660,
  sparkle: 880,
  water: 420,
  sticker: 740,
})

export function createSceneAudioController(scope = globalThis) {
  let context = null

  const speakTamil = (text, { enabled = true, activated = false } = {}) => {
    if (!enabled || !activated || !text || !scope?.speechSynthesis || !scope?.SpeechSynthesisUtterance) return false
    scope.speechSynthesis.cancel()
    const utterance = new scope.SpeechSynthesisUtterance(text)
    utterance.lang = 'ta-IN'
    utterance.rate = 0.88
    utterance.pitch = 1.05
    scope.speechSynthesis.speak(utterance)
    return true
  }

  const playEffect = (name, { enabled = true, activated = false } = {}) => {
    const frequency = EFFECT_FREQUENCIES[name]
    const AudioContextCtor = scope?.AudioContext || scope?.webkitAudioContext
    if (!enabled || !activated || !frequency || !AudioContextCtor) return false
    try {
      if (!context || context.state === 'closed') context = new AudioContextCtor()
      const oscillator = context.createOscillator()
      const gain = context.createGain()
      oscillator.frequency.value = frequency
      oscillator.connect(gain)
      gain.connect(context.destination)
      gain.gain.setValueAtTime(0.0001, context.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.18)
      oscillator.start(context.currentTime)
      oscillator.stop(context.currentTime + 0.2)
      return true
    } catch {
      return false
    }
  }

  const stop = () => {
    scope?.speechSynthesis?.cancel?.()
    if (context && context.state !== 'closed') context.close?.()
    context = null
  }

  return { speakTamil, playEffect, stop }
}

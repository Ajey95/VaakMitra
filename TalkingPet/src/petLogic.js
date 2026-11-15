export function getPetResponse(transcript) {
  const phrase = String(transcript || '').trim()
  return phrase || 'Say something and I will repeat it!'
}

export function getPetMood({ isListening = false, isSpeaking = false, hasTranscript = false } = {}) {
  if (isListening) return 'listening'
  if (isSpeaking) return 'speaking'
  if (hasTranscript) return 'happy'
  return 'idle'
}

export function getSpeechRecognitionConstructor(scope = globalThis) {
  return scope?.SpeechRecognition || scope?.webkitSpeechRecognition || null
}

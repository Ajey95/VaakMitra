const DEFAULT_NAME = 'Mitra'

export function getAvatarCoachMessage({ slide = 1, lesson = {}, outcome = null }) {
  const word = lesson.english || lesson.phoneme || 'this sound'
  const tip = lesson.tip || 'Take your time and try again.'

  if (outcome === 'success') return lesson.avatar_coach?.success || `Great job with ${word}! You did it!`
  if (outcome === 'retry') return lesson.avatar_coach?.retry || `Nice try with ${word}. Let's practice once more.`

  switch (slide) {
    case 2:
      return `Watch closely. Listen to how ${word} sounds.`
    case 3:
      return `Your turn! Say ${word} out loud. I am listening.`
    case 4:
      return `Let's practise the breath for ${word}. Blow gently!`
    case 5:
      return `You worked hard today. You are a star!`
    default:
      return lesson.avatar_coach?.intro || `Let's learn ${word} together!`
  }
}

export function getAvatarCoachMood({ slide = 1, outcome = null, isRecording = false }) {
  if (outcome === 'success') return 'celebrate'
  if (outcome === 'retry') return 'encourage'
  if (isRecording) return 'listen'
  if (slide === 4) return 'thinking'
  if (slide === 5) return 'celebrate'
  if (slide === 2) return 'happy'
  return 'idle'
}

export function getAvatarCoachName(lesson) {
  return lesson?.avatar_coach?.name || DEFAULT_NAME
}

export function canSpeakWithBrowser() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window
}


const wordFor = (lesson = {}) => getPippinTargetText(lesson)

const PHONEME_SPEECH_CUES = Object.freeze({
  a: 'Ahhhhh',
  aa: 'Aaaaaahhhhh',
  la: 'lah',
  ta: 'tah',
  amma: 'um-mah',
  appa: 'up-pah',
})

export function getPippinTargetText(lesson = {}) {
  const phoneme = String(lesson.phoneme || '').trim().toLowerCase()
  return String(PHONEME_SPEECH_CUES[phoneme] || lesson.english || lesson.symbol || 'this sound')
    .replace(/\s+/g, ' ')
    .trim()
}

export function getTrainingPippinState({
  lesson = {},
  slide = 1,
  isRecording = false,
  isRepeating = false,
  isAnalyzing = false,
  outcome = null,
} = {}) {
  const word = wordFor(lesson)

  if (outcome === 'success') {
    return { phase: 'complete', mood: 'dance', message: `Great ${word}! You said it clearly.` }
  }
  if (outcome === 'retry') {
    return { phase: 'listen', mood: 'encourage', message: `Let us listen to ${word} and try once more.` }
  }
  if (isAnalyzing) {
    return { phase: 'evaluate', mood: 'preparing', message: `I am evaluating your ${word} sound.` }
  }
  if (isRepeating) {
    return { phase: 'repeat', mood: 'repeating', message: `I am repeating your ${word} sound.` }
  }
  if (isRecording) {
    return { phase: 'listen', mood: 'listening', message: `I am listening for ${word}.` }
  }

  switch (slide) {
    case 2:
      return { phase: 'listen', mood: 'repeating', message: `Listen to ${word}, then repeat it.` }
    case 3:
      return { phase: 'listen', mood: 'ready', message: `Say ${word}. I will listen, repeat, and evaluate.` }
    case 4:
      return { phase: 'listen', mood: 'encourage', message: `Listen and practise the breath for ${word}.` }
    case 5:
      return { phase: 'complete', mood: 'dance', message: `You finished ${word}. Well done!` }
    default:
      return { phase: 'listen', mood: 'ready', message: `Listen closely to ${word}.` }
  }
}

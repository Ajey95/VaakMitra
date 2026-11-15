const TAMIL_PROMPTS = Object.freeze({
  'breath-balloon': Object.freeze({
    intro: 'வணக்கம்! இன்று நம்ம பலூனை வானத்தில் பறக்க விடலாமா?',
    'too-weak': 'சிறிது பலமாக முயற்சி செய்வோம்.',
    steady: 'அப்படியே மெதுவாக ஊதுங்கள்!',
    'too-strong': 'மிக வேகமாக இல்லை… மெதுவாக ஊதுங்கள்.',
    stopped: 'பரவாயில்லை! இன்னும் கொஞ்சம் மெதுவாக ஊதலாம்.',
    success: 'அருமை! பலூன் மேலே பறக்கிறது!',
    complete: 'அருமை! நீங்க ரொம்ப நல்லா செய்தீங்க!',
  }),
  'river-rescue': Object.freeze({
    intro: 'எனக்கு வீட்டிற்குச் செல்ல உதவுவாயா?',
    retry: 'பரவாயில்லை… இன்னொரு முறை முயற்சி செய்வோம்.',
    success: 'அருமை! கவி அடுத்த படிக்குச் செல்கிறான்!',
    complete: 'அருமை! கவி பாதுகாப்பாகக் கடந்துவிட்டான்!',
  }),
  'mouth-mirror': Object.freeze({
    matched: 'சரியாக செய்தாய்!',
    retry: 'மீண்டும் மெதுவாக முயற்சி செய்வோம்.',
  }),
  'talk-together': Object.freeze({
    independent: 'சிறப்பாக பேசினாய்!',
    prompted: 'மிகவும் அருமை!',
    complete: 'நீங்கள் தினமும் இன்னும் சிறப்பாக முன்னேறுகிறீர்கள்!',
  }),
})

export function getBreathVisualState({ mode, level, target = [0.25, 0.7] }) {
  if (['success', 'support', 'complete'].includes(mode)) return mode === 'support' ? 'stopped' : mode
  if (mode !== 'playing') return mode === 'intro' ? 'intro' : 'idle'
  if (level < target[0]) return 'too-weak'
  if (level > target[1]) return 'too-strong'
  return 'steady'
}

export function getEffectProfile({ motionLevel = 'full', celebrationLevel = 'gentle' } = {}) {
  if (motionLevel === 'minimal' || celebrationLevel === 'none') {
    return { ambient: false, particles: 0, travel: false, durationMs: 0 }
  }
  if (motionLevel === 'reduced' || celebrationLevel === 'gentle') {
    return { ambient: true, particles: 6, travel: false, durationMs: 1800 }
  }
  return { ambient: true, particles: 18, travel: true, durationMs: 4000 }
}

export function getTamilPrompt(game, state) {
  return TAMIL_PROMPTS[game]?.[state] || ''
}

export const TALK_TOGETHER_SCENES = Object.freeze([
  { id: 'ask-water', environment: 'kitchen', title: 'தண்ணீர் கேட்போம்' },
  { id: 'choose-snack', environment: 'grocery', title: 'சிற்றுண்டி தேர்வு' },
  { id: 'name-object', environment: 'classroom', title: 'பொருளைக் கண்டுபிடிப்போம்' },
  { id: 'imitate-turns', environment: 'park', title: 'மாறி மாறிச் செய்வோம்' },
  { id: 'say-thanks', environment: 'birthday', title: 'நன்றி சொல்வோம்' },
])

export function getTalkTogetherReward(assistance) {
  if (assistance === 'independent') return { intensity: 'full', promptKey: 'independent' }
  if (assistance === 'skipped') return { intensity: 'none', promptKey: '' }
  return { intensity: 'gentle', promptKey: 'prompted' }
}

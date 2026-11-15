export const PIPPIN_INTENTS = new Set(['jump', 'dance', 'sleep', 'eat', 'hello', 'ball', 'amma', 'appa', 'a', 'aa', 'la'])

const TAMIL_ALIASES = new Map([
  ['அம்மா', 'amma'], ['அப்பா', 'appa'], ['அ', 'a'], ['ஆ', 'aa'], ['ல', 'la'],
])

const RESPONSES = {
  jump: 'Boing! Pippin jumped for you!',
  dance: 'Wiggle, wiggle! Let us dance!',
  sleep: 'Yawn... Pippin is having a tiny nap.',
  eat: 'Crunch, crunch! A tasty pretend snack.',
  hello: 'Hello, friend! Pippin is happy to see you.',
  ball: 'Ball! Pippin found the blue ball.',
  amma: 'Amma. That is a warm, important word.',
  appa: 'Appa. Pippin heard that clearly.',
  a: 'A. A short, open sound.',
  aa: 'Aa. A long, open sound.',
  la: 'La. Touch up behind your teeth.',
}

const UNSAFE_WORDS = /\b(kill|hurt|hate|die|weapon)\b/i

export function matchPippinIntent(text) {
  const words = String(text || '').toLocaleLowerCase().match(/[\p{L}\p{M}]+/gu) || []
  for (const word of words) {
    const intent = TAMIL_ALIASES.get(word) || word
    if (PIPPIN_INTENTS.has(intent)) return intent
  }
  return 'repeat'
}

function safePhrase(text) {
  const printable = Array.from(String(text || ''))
    .filter((character) => character.charCodeAt(0) >= 32 && character.charCodeAt(0) !== 127)
    .join('')
  return printable
    .replace(/https?:\/\/\S+/gi, '')
    .trim()
    .split(/\s+/)
    .slice(0, 6)
    .join(' ')
    .slice(0, 80)
}

export function getPippinResponse(intent, text = '') {
  if (RESPONSES[intent]) return RESPONSES[intent]
  const phrase = safePhrase(text)
  if (!phrase || UNSAFE_WORDS.test(phrase)) return 'I heard your voice. Let us try a kind word together.'
  if (!phrase.includes(' ')) return `${phrase.charAt(0).toLocaleUpperCase()}${phrase.slice(1)}! What a bright word.`
  return `I heard you! You said “${phrase}”.`
}

export function appendLocalHistory(history, item) {
  return [item, ...(Array.isArray(history) ? history : [])].slice(0, 5)
}

export function toPippinReport(history) {
  return (Array.isArray(history) ? history : []).map(({ intent }) => ({ intent: PIPPIN_INTENTS.has(intent) ? intent : 'repeat' }))
}

export function resetPippinState() {
  return { history: [], intentCounts: {}, interactionCount: 0 }
}

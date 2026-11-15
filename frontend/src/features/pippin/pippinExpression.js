const BASE_EXPRESSION = Object.freeze({
  face: 'smile',
  blink: 'gentle',
  ears: 'relaxed',
  tail: 'gentle',
  body: 'breathing',
  paws: 'still',
})

const EXPRESSIONS = Object.freeze({
  listening: Object.freeze({ face: 'focused', blink: 'alert', ears: 'forward', tail: 'slow', body: 'listening', paws: 'still' }),
  preparing: Object.freeze({ face: 'curious', blink: 'alert', ears: 'forward', tail: 'slow', body: 'breathing', paws: 'still' }),
  repeating: Object.freeze({ face: 'speaking', blink: 'gentle', ears: 'perked', tail: 'happy', body: 'talking', paws: 'bounce' }),
  sing: Object.freeze({ face: 'speaking', blink: 'gentle', ears: 'perked', tail: 'happy', body: 'singing', paws: 'bounce' }),
  dance: Object.freeze({ face: 'wide-smile', blink: 'happy', ears: 'perked', tail: 'fast', body: 'dancing', paws: 'dance' }),
  ready: Object.freeze({ ...BASE_EXPRESSION, ears: 'forward', tail: 'happy' }),
  encourage: Object.freeze({ ...BASE_EXPRESSION, face: 'soft-smile', blink: 'slow', ears: 'soft', tail: 'slow' }),
})

export function getPippinExpression(mood = 'idle', audioLevel = 0) {
  const expression = EXPRESSIONS[mood] || BASE_EXPRESSION
  if (Number(audioLevel) > 0.12 && !['listening', 'preparing'].includes(mood) && expression.face !== 'speaking') {
    return { ...expression, face: 'speaking', body: 'talking' }
  }
  return { ...expression }
}

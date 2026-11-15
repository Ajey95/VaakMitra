import { APPLICATION_VOICE_PROFILE_ID, speakCharacter } from '../characters/characterVoice'

const ROUND_LETTERS = Object.freeze([
  Object.freeze([['A', 'ah'], ['B', 'buh'], ['M', 'mmm']]),
  Object.freeze([['P', 'puh'], ['L', 'lll'], ['S', 'sss']]),
  Object.freeze([['T', 'tuh'], ['K', 'kuh'], ['R', 'rrr']]),
])

const THRESHOLDS = Object.freeze([0.24, 0.5, 0.76])

export const LETTER_FLIGHT_ROUNDS = Object.freeze(ROUND_LETTERS.map((letters, roundIndex) => (
  Object.freeze(letters.map(([letter, sound], gateIndex) => Object.freeze({
    id: `round-${roundIndex + 1}-${letter.toLowerCase()}`,
    letter,
    sound,
    threshold: THRESHOLDS[gateIndex],
  })))
)))

export function findNewlyCrossedLetters({ previousLevel, currentLevel, obstacles, crossedIds }) {
  const previous = Math.max(0, Math.min(1, Number(previousLevel) || 0))
  const current = Math.max(0, Math.min(1, Number(currentLevel) || 0))
  if (current <= previous) return []
  const completed = crossedIds instanceof Set ? crossedIds : new Set(crossedIds || [])
  return obstacles.filter((obstacle) => (
    !completed.has(obstacle.id)
    && obstacle.threshold > previous
    && obstacle.threshold <= current
  ))
}

export function speakCuteLetterSound(scope, obstacle) {
  if (!scope?.speechSynthesis || !scope?.SpeechSynthesisUtterance || !obstacle?.sound) return false
  return speakCharacter(obstacle.sound, {
    synthesis: scope.speechSynthesis,
    UtteranceCtor: scope.SpeechSynthesisUtterance,
    profileId: APPLICATION_VOICE_PROFILE_ID,
    language: 'en-IN',
    overrides: { pitch: 1.75, rate: 0.68 },
  })
}

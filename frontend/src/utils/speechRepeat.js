import { APPLICATION_VOICE_PROFILE_ID, speakCharacter } from '../features/characters/characterVoice'

export function repeatPhrase(text, { scope = globalThis, lang = 'en-IN', onStart, onEnd, onError } = {}) {
  const phrase = String(text || '').trim()
  if (!phrase || !scope?.speechSynthesis || !scope?.SpeechSynthesisUtterance) return false

  return speakCharacter(phrase, {
    synthesis: scope.speechSynthesis,
    UtteranceCtor: scope.SpeechSynthesisUtterance,
    profileId: APPLICATION_VOICE_PROFILE_ID,
    guided: true,
    language: lang,
    onStart,
    onEnd,
    onError,
  })
}

export function repeatPhraseWithPraise(text, {
  scope = globalThis,
  lang = 'en-IN',
  praise = 'Very good!',
  onStart,
  onPraiseStart,
  onEnd,
  onError,
} = {}) {
  let settled = false
  const finish = (callback, value) => {
    if (settled) return
    settled = true
    callback?.(value)
  }
  const fail = (error) => finish(onError, error)
  const speakPraise = () => {
    const praised = speakCharacter(praise, {
      synthesis: scope?.speechSynthesis,
      UtteranceCtor: scope?.SpeechSynthesisUtterance,
      profileId: APPLICATION_VOICE_PROFILE_ID,
      language: 'en-IN',
      onStart: onPraiseStart,
      onEnd: () => finish(onEnd),
      onError: fail,
    })
    if (!praised) fail()
  }

  const repeated = repeatPhrase(text, {
    scope,
    lang,
    onStart,
    onEnd: speakPraise,
    onError: fail,
  })
  if (!repeated) fail()
  return repeated
}

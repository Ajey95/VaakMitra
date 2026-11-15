import { describe, expect, it } from 'vitest'
import { getPetResponse, getPetMood, getSpeechRecognitionConstructor } from './petLogic'

describe('talking pet behavior', () => {
  it('returns the child phrase directly for an exact repeat', () => {
    expect(getPetResponse('hello Pippin')).toBe('hello Pippin')
    expect(getPetResponse('  hello again  ')).toBe('hello again')
    expect(getPetResponse('   ')).toBe('Say something and I will repeat it!')
  })

  it('maps speaking and listening to expressive moods', () => {
    expect(getPetMood({ isListening: true, isSpeaking: false })).toBe('listening')
    expect(getPetMood({ isListening: false, isSpeaking: true })).toBe('speaking')
    expect(getPetMood({ isListening: false, isSpeaking: false, hasTranscript: true })).toBe('happy')
  })

  it('detects the browser speech recognition implementation', () => {
    expect(getSpeechRecognitionConstructor({ SpeechRecognition: class Modern {} })).toBeTypeOf('function')
    expect(getSpeechRecognitionConstructor({ webkitSpeechRecognition: class Webkit {} })).toBeTypeOf('function')
    expect(getSpeechRecognitionConstructor({})).toBeNull()
  })
})

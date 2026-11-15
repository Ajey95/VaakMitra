import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Check, Ear, RotateCcw, Sparkles, Volume2, VolumeX, Waves } from 'lucide-react'
import PippinStorybook from '../storybook/PippinStorybook'
import { getTrainingPippinState } from '../../features/pippin/trainingPippin'
import {
  APPLICATION_VOICE_PROFILE_ID,
  speakCharacter,
  stopCharacterSpeech,
  watchInstalledVoices,
} from '../../features/characters/characterVoice'
import { useSettingsStore } from '../../store/settingsStore'
import '../interactive/play.css'

const STEPS = [
  { id: 'listen', label: 'Listen', icon: Ear },
  { id: 'repeat', label: 'Repeat', icon: RotateCcw },
  { id: 'evaluate', label: 'Evaluate', icon: Waves },
]

export default function PippinTrainingCoach({ lesson, slide, activity = {} }) {
  const { autoPlay, soundEnabled, setSoundEnabled } = useSettingsStore()
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [voiceAvailable, setVoiceAvailable] = useState(true)
  const [voicesVersion, setVoicesVersion] = useState(0)
  const knownVoicesRef = useRef(null)
  if (knownVoicesRef.current === null) {
    try {
      knownVoicesRef.current = (window.speechSynthesis?.getVoices?.() || []).length > 0
    } catch {
      knownVoicesRef.current = false
    }
  }
  const state = useMemo(
    () => getTrainingPippinState({ lesson, slide, ...activity }),
    [activity, lesson, slide],
  )
  const activeIndex = state.phase === 'repeat' ? 1 : state.phase === 'evaluate' ? 2 : state.phase === 'complete' ? 3 : 0

  const speakMessage = useCallback((force = false) => {
    if (!force && !soundEnabled) return false
    const spoken = speakCharacter(state.message, {
      profileId: APPLICATION_VOICE_PROFILE_ID,
      guided: true,
      language: 'en-IN',
      enabled: force || soundEnabled,
      onStart: () => {
        setVoiceAvailable(true)
        setIsSpeaking(true)
      },
      onEnd: () => setIsSpeaking(false),
      onError: () => {
        setIsSpeaking(false)
        setVoiceAvailable(false)
      },
    })
    if (!spoken) {
      setIsSpeaking(false)
      setVoiceAvailable(false)
    }
    return spoken
  }, [soundEnabled, state.message])

  useEffect(() => {
    if (activity.isRecording) {
      stopCharacterSpeech()
      setIsSpeaking(false)
      return undefined
    }
    const responseSequenceActive = activity.isRepeating
      || activity.isAnalyzing
      || (activity.hasRecording && !activity.outcome)
    // The evaluation slide owns its target -> validation -> praise sequence.
    // Keep the outcome message visual so it cannot interrupt or duplicate it.
    if (!autoPlay || !soundEnabled || responseSequenceActive || activity.outcome) return undefined
    const timer = window.setTimeout(() => speakMessage(), 80)
    return () => {
      window.clearTimeout(timer)
    }
  }, [activity.hasRecording, activity.isAnalyzing, activity.isRecording, activity.isRepeating, activity.outcome, autoPlay, soundEnabled, speakMessage, voicesVersion])

  useEffect(() => watchInstalledVoices(window.speechSynthesis, (voices) => {
    if (voices.length > 0 && !knownVoicesRef.current) {
      knownVoicesRef.current = true
      setVoicesVersion((version) => version + 1)
    }
  }), [])

  useEffect(() => () => stopCharacterSpeech(), [])

  const handleSpeak = () => {
    if (!soundEnabled) setSoundEnabled(true)
    speakMessage(true)
  }

  return (
    <aside className="training-pippin" data-testid="pippin-training-panel" aria-label="Pippin training coach">
      <header className="training-pippin__header">
        <span><Sparkles aria-hidden="true" /> Pippin</span>
        <strong>Practice coach</strong>
      </header>

      <PippinStorybook
        mood={state.mood}
        audioLevel={isSpeaking ? 0.55 : activity.audioLevel || 0}
        message={state.message}
      />

      <p className="training-pippin__message" aria-live="polite">{state.message}</p>
      <button
        type="button"
        className="training-pippin__voice"
        onClick={handleSpeak}
        aria-label={soundEnabled ? 'Hear Pippin' : 'Turn on Pippin voice'}
        data-speaking={isSpeaking ? 'true' : 'false'}
      >
        {soundEnabled ? <Volume2 aria-hidden="true" /> : <VolumeX aria-hidden="true" />}
        <span>{isSpeaking ? 'Pippin is speaking' : soundEnabled ? 'Hear Pippin' : 'Turn on voice'}</span>
      </button>
      {!voiceAvailable && <p className="training-pippin__voice-status" role="status">Voice is unavailable on this device.</p>}
      <ol className="training-pippin__steps" aria-label="Listen, repeat, and evaluate">
        {STEPS.map(({ id, label, icon: Icon }, index) => {
          const complete = activeIndex > index
          const active = activeIndex === index
          return (
            <li key={id} data-state={complete ? 'complete' : active ? 'active' : 'upcoming'}>
              <span>{complete ? <Check aria-hidden="true" /> : <Icon aria-hidden="true" />}</span>
              <small>{label}</small>
            </li>
          )
        })}
      </ol>
    </aside>
  )
}

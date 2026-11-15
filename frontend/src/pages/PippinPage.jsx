import { useCallback, useEffect, useRef, useState } from 'react'
import { Mic, Music2, Play, ShieldCheck, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import InteractiveSessionShell from '../components/interactive/InteractiveSessionShell'
import PippinStorybook from '../components/storybook/PippinStorybook'
import {
  APPLICATION_VOICE_PROFILE_ID,
  speakCharacter,
  stopCharacterSpeech,
} from '../features/characters/characterVoice'
import { readAnalyserLevel } from '../features/interactive/audioLevel'
import { buildKittenEchoReport, createKittenEcho } from '../features/storybook/kittenEcho'
import { createVoiceTurnDetector } from '../features/storybook/voiceTurnDetector'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { interactiveSessionsAPI } from '../services/api'
import { useInteractionSettingsStore } from '../store/interactionSettingsStore'

const COPY = {
  welcome: 'Hello! I repeat your words / வணக்கம்! நீங்கள் சொல்வதை நான் திரும்பச் சொல்வேன்',
  listening: 'Listening / கேட்கிறேன்',
  preparing: 'Getting ready / தயாராகிறேன்',
  repeating: 'Pippin repeats / பிப்பின் திரும்பச் சொல்கிறான்',
  ready: 'I am ready for your next words / உங்கள் அடுத்த வார்த்தைகளுக்கு நான் தயார்',
  unavailable: 'Microphone unavailable. Choose a phrase / மைக்ரோஃபோன் கிடைக்கவில்லை. ஒரு சொல்லைத் தேர்ந்தெடுக்கலாம்.',
  privacy: 'Your voice stays on this device and is not saved / உங்கள் குரல் இந்தச் சாதனத்திலேயே இருக்கும்; சேமிக்கப்படாது.',
}

const FALLBACK_PHRASES = [
  { label: 'Hello / வணக்கம்', speech: 'Hello. வணக்கம்' },
  { label: 'Mother / அம்மா', speech: 'Mother. அம்மா' },
  { label: 'Come, Kavi / கவி வா', speech: 'Come, Kavi. கவி வா' },
]

const BILINGUAL_SHELL_LABELS = {
  locale: 'bi',
  playPractice: 'Play & Practice / விளையாடிப் பழகலாம்',
  exit: 'Exit activity / வெளியே செல்லுங்கள்',
  calm: 'Calm / அமைதி',
  settings: 'Comfort settings / வசதி அமைப்புகள்',
  resume: 'Resume / தொடருங்கள்',
  pause: 'Pause / இடைநிறுத்துங்கள்',
}

function playPippinSong(scope) {
  const AudioContextCtor = scope.AudioContext || scope.webkitAudioContext
  if (!AudioContextCtor) return () => {}
  const context = new AudioContextCtor()
  const notes = [523, 659, 784, 659, 523]
  notes.forEach((frequency, index) => {
    const oscillator = context.createOscillator()
    const gain = context.createGain()
    oscillator.type = 'sine'
    oscillator.frequency.setValueAtTime(frequency, context.currentTime + index * .18)
    gain.gain.setValueAtTime?.(.0001, context.currentTime)
    gain.gain.exponentialRampToValueAtTime?.(.12, context.currentTime + index * .18 + .02)
    gain.gain.exponentialRampToValueAtTime?.(.0001, context.currentTime + index * .18 + .16)
    oscillator.connect(gain)
    gain.connect(context.destination)
    oscillator.start(context.currentTime + index * .18)
    oscillator.stop(context.currentTime + index * .18 + .17)
  })
  return () => context.close().catch(() => {})
}

export default function PippinPage() {
  const navigate = useNavigate()
  const { preferences } = useInteractionSettingsStore()
  const [mood, setMood] = useState('idle')
  const [message, setMessage] = useState(COPY.welcome)
  const [audioLevel, setAudioLevel] = useState(0)
  const [activated, setActivated] = useState(false)
  const [hasPlayed, setHasPlayed] = useState(false)
  const [microphoneUnavailable, setMicrophoneUnavailable] = useState(false)
  const echoRef = useRef(null)
  const detectorRef = useRef(createVoiceTurnDetector())
  const monitorFrameRef = useRef(0)
  const restartTimerRef = useRef(0)
  const returnTimerRef = useRef(0)
  const songStopRef = useRef(() => {})
  const autoModeRef = useRef(false)
  const startInFlightRef = useRef(false)
  const turnActionRef = useRef(null)
  const mountedRef = useRef(false)
  const beginAutomaticTurnRef = useRef(() => {})
  const startedAtRef = useRef(Date.now())
  const repeatCountRef = useRef(0)
  const { isRecording, audioBlob, analyserRef, startRecording, stopRecording, resetRecording } = useAudioRecorder()

  const stopMonitoring = useCallback(() => {
    window.cancelAnimationFrame(monitorFrameRef.current)
    monitorFrameRef.current = 0
    setAudioLevel(0)
  }, [])

  const monitorTurn = useCallback(() => {
    if (!autoModeRef.current || !mountedRef.current) return
    const level = readAnalyserLevel(analyserRef.current)
    setAudioLevel(level)
    const outcome = detectorRef.current.sample(level, performance.now())
    if (outcome.event === 'turn-complete' || outcome.event === 'max-duration') {
      stopMonitoring()
      turnActionRef.current = outcome.hasSpeech ? 'replay' : 'restart'
      setMood('preparing')
      setMessage(COPY.preparing)
      stopRecording()
      return
    }
    monitorFrameRef.current = window.requestAnimationFrame(monitorTurn)
  }, [analyserRef, stopMonitoring, stopRecording])

  const beginAutomaticTurn = useCallback(async () => {
    if (!mountedRef.current || !autoModeRef.current || startInFlightRef.current) return
    startInFlightRef.current = true
    window.clearTimeout(restartTimerRef.current)
    stopMonitoring()
    echoRef.current?.stop()
    stopCharacterSpeech()
    resetRecording()
    detectorRef.current.reset(performance.now())
    const allowed = await startRecording('en-IN', { speechRecognition: false, repeatRecognized: false })
    startInFlightRef.current = false

    if (!mountedRef.current || !autoModeRef.current) {
      if (allowed) resetRecording()
      return
    }
    if (!allowed) {
      autoModeRef.current = false
      setMicrophoneUnavailable(true)
      setMood('encourage')
      setMessage(COPY.unavailable)
      return
    }

    setMicrophoneUnavailable(false)
    setMood('listening')
    setMessage(COPY.listening)
    monitorFrameRef.current = window.requestAnimationFrame(monitorTurn)
  }, [monitorTurn, resetRecording, startRecording, stopMonitoring])

  useEffect(() => {
    beginAutomaticTurnRef.current = beginAutomaticTurn
  }, [beginAutomaticTurn])

  useEffect(() => {
    mountedRef.current = true
    echoRef.current = createKittenEcho({ scope: window, onLevel: setAudioLevel })
    return () => {
      mountedRef.current = false
      autoModeRef.current = false
      turnActionRef.current = null
      window.cancelAnimationFrame(monitorFrameRef.current)
      window.clearTimeout(restartTimerRef.current)
      window.clearTimeout(returnTimerRef.current)
      songStopRef.current()
      echoRef.current?.dispose()
      stopCharacterSpeech()
      resetRecording()
    }
  }, [resetRecording])

  useEffect(() => {
    const action = turnActionRef.current
    if (!action || !audioBlob) return
    turnActionRef.current = null
    if (!autoModeRef.current) return

    if (action === 'restart') {
      restartTimerRef.current = window.setTimeout(() => beginAutomaticTurnRef.current(), 250)
      return
    }

    const repeatLocally = async () => {
      setHasPlayed(true)
      setMood('repeating')
      setMessage(COPY.repeating)
      repeatCountRef.current += 1
      try {
        await echoRef.current?.play(audioBlob)
      } finally {
        if (mountedRef.current && autoModeRef.current) {
          setMood('ready')
          setMessage(COPY.ready)
          restartTimerRef.current = window.setTimeout(() => beginAutomaticTurnRef.current(), 350)
        }
      }
    }
    repeatLocally()
  }, [audioBlob])

  const enableMicrophone = () => {
    setActivated(true)
    setMicrophoneUnavailable(false)
    autoModeRef.current = true
    beginAutomaticTurnRef.current()
  }

  const suspendHandsFree = useCallback(() => {
    autoModeRef.current = false
    turnActionRef.current = null
    window.clearTimeout(restartTimerRef.current)
    stopMonitoring()
    echoRef.current?.stop()
    stopCharacterSpeech()
    if (isRecording) stopRecording()
  }, [isRecording, stopMonitoring, stopRecording])

  const resumeAfterActivity = (messageAfter) => {
    window.clearTimeout(returnTimerRef.current)
    returnTimerRef.current = window.setTimeout(() => {
      if (!mountedRef.current) return
      if (activated && !microphoneUnavailable) {
        autoModeRef.current = true
        beginAutomaticTurnRef.current()
      } else {
        setMood('ready')
        setMessage(messageAfter)
      }
    }, 2600)
  }

  const dance = () => {
    suspendHandsFree()
    songStopRef.current()
    setMood('dance')
    setMessage('Dance with me / என்னுடன் ஆடுங்கள்')
    resumeAfterActivity(COPY.welcome)
  }

  const sing = () => {
    suspendHandsFree()
    songStopRef.current()
    setMood('sing')
    setMessage('Sing with me / என்னுடன் பாடுங்கள்')
    songStopRef.current = playPippinSong(window)
    speakCharacter('Meow meow, little friend! மியாவ் மியாவ், குட்டி நண்பா!', {
      profileId: APPLICATION_VOICE_PROFILE_ID, language: 'en-IN', enabled: preferences.soundEnabled,
    })
    resumeAfterActivity(COPY.welcome)
  }

  const playFixedPhrase = ({ label, speech }) => {
    setMood('sing')
    setMessage(label)
    speakCharacter(speech, { profileId: APPLICATION_VOICE_PROFILE_ID, language: 'en-IN', enabled: preferences.soundEnabled })
  }

  const reset = () => {
    suspendHandsFree()
    window.clearTimeout(returnTimerRef.current)
    songStopRef.current()
    resetRecording()
    setActivated(false)
    setHasPlayed(false)
    setMicrophoneUnavailable(false)
    setMood('idle')
    setMessage(COPY.welcome)
  }

  const leave = () => {
    suspendHandsFree()
    interactiveSessionsAPI.create(buildKittenEchoReport({
      startedAt: startedAtRef.current,
      completedAt: Date.now(),
      repeatCount: repeatCountRef.current,
    })).catch(() => {})
    navigate('/play')
  }

  const listening = mood === 'listening'

  return (
    <InteractiveSessionShell
      title="Talk with Pippin / பிப்பினுடன் பேசலாம்"
      subtitle="Speak naturally; Pippin repeats locally / இயல்பாகப் பேசுங்கள்; பிப்பின் திரும்பச் சொல்லும்"
      state={{ phase: mood, stepIndex: 0 }}
      onExit={leave}
      labels={BILINGUAL_SHELL_LABELS}
    >
      <div className="pippin-story-layout">
        <PippinStorybook mood={mood} audioLevel={audioLevel} motionLevel={preferences.motionLevel} message={message} />
        <section className="pippin-story-card" aria-live="polite">
          <span className="pippin-story-kicker"><Sparkles aria-hidden="true" /> Your kitten friend / உங்கள் குட்டிப் பூனை நண்பன்</span>
          <h2 className={listening ? 'pippin-listening-status' : ''}>{message}</h2>
          <div className="pippin-story-actions">
            {!activated ? (
              <button className="pippin-story-button pippin-story-button--primary" type="button" onClick={enableMicrophone}>
                <Mic aria-hidden="true" /> Enable microphone / மைக்ரோஃபோனை இயக்கவும்
              </button>
            ) : null}
            <button className="pippin-story-button" type="button" onClick={dance}><Play aria-hidden="true" /> Dance / ஆடு</button>
            <button className="pippin-story-button" type="button" onClick={sing}><Music2 aria-hidden="true" /> Sing / பாடு</button>
          </div>
          {microphoneUnavailable ? (
            <div className="pippin-fixed-words" aria-label="Choose a phrase / சொல்லைத் தேர்ந்தெடுக்கவும்">
              {FALLBACK_PHRASES.map((phrase) => (
                <button type="button" key={phrase.label} onClick={() => playFixedPhrase(phrase)}>{phrase.label}</button>
              ))}
            </div>
          ) : null}
          <p className="pippin-story-privacy"><ShieldCheck aria-hidden="true" /> {COPY.privacy}</p>
          {activated || hasPlayed ? <button className="pippin-story-reset" type="button" onClick={reset}>New game / புதிய விளையாட்டு</button> : null}
        </section>
      </div>
    </InteractiveSessionShell>
  )
}

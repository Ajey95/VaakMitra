import { useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { BookOpen, Ear, HelpCircle, Mic, RotateCcw, Sparkles, Square, Volume2 } from 'lucide-react'
import KaviStorybookScene from '../components/storybook/KaviStorybookScene'
import InteractiveSessionShell from '../components/interactive/InteractiveSessionShell'
import { TamilStatus } from '../components/interactive/SceneEffects'
import { createStoryNarrator } from '../features/characters/characterVoice'
import { readAnalyserLevel } from '../features/interactive/audioLevel'
import { getEffectProfile, getTamilPrompt } from '../features/interactive/animationPresentation'
import { createSceneAudioController } from '../features/interactive/sceneAudio'
import {
  KAVI_STORY_PAGES,
  buildKaviStoryReport,
  createKaviStoryState,
  getKaviPage,
  kaviStoryReducer,
} from '../features/storybook/kaviStory'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { interactiveSessionsAPI, storyVoiceAPI } from '../services/api'
import { useInteractionSettingsStore } from '../store/interactionSettingsStore'

const FEEDBACK = {
  wonderful: 'அருமை! மிக அழகாகச் சொன்னீர்கள்!',
  almost: 'நன்றாக முயன்றீர்கள்! இன்னொரு முறை மெதுவாகச் சொல்லலாமா?',
  try_together: 'கவியுடன் சேர்ந்து மெதுவாகச் சொல்லலாம்.',
  model_unavailable: 'நான் கேட்கிறேன். படத்தைப் பார்த்து நாமே சேர்ந்து சொல்லலாம்.',
  audio_unavailable: 'ஒலி தெளிவாகக் கேட்கவில்லை. படத்துடன் சேர்ந்து சொல்லலாம்.',
  complete: 'அருமை! கவி பாலத்தைக் கடந்துவிட்டான்!',
}

const TAMIL_SHELL_LABELS = {
  locale: 'ta',
  playPractice: 'விளையாடிப் பழகலாம்',
  exit: 'வெளியே செல்லுங்கள்',
  calm: 'அமைதி',
  settings: 'வசதி அமைப்புகள்',
  resume: 'தொடருங்கள்',
  pause: 'இடைநிறுத்துங்கள்',
}

function moodFor(phase, isSpeaking) {
  if (isSpeaking || phase === 'narrating') return 'speaking'
  if (phase === 'listening' || phase === 'evaluating') return 'listening'
  if (phase === 'success' || phase === 'complete') return 'celebrate'
  if (phase === 'support') return 'encourage'
  if (phase === 'walking') return 'walking'
  if (phase === 'ready') return 'ready'
  return 'idle'
}

export default function RiverRescuePage() {
  const [state, dispatch] = useReducer(kaviStoryReducer, undefined, () => createKaviStoryState(Date.now()))
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const [walkingProgress, setWalkingProgress] = useState(0)
  const submittedBlobRef = useRef(null)
  const reportSentRef = useRef(false)
  const narratorRef = useRef(null)
  const feedbackSpokenRef = useRef('')
  const sceneAudioRef = useRef(null)
  const sceneAudioActivatedRef = useRef(false)
  const previousScenePhaseRef = useRef('intro')
  const { preferences } = useInteractionSettingsStore()
  const {
    isRecording,
    audioBlob,
    analyserRef,
    startRecording,
    stopRecording,
    resetRecording,
  } = useAudioRecorder()
  const page = getKaviPage(state)
  const effectProfile = getEffectProfile(preferences)
  const animationPrompt = state.phase === 'intro'
    ? getTamilPrompt('river-rescue', 'intro')
    : state.phase === 'support'
      ? getTamilPrompt('river-rescue', 'retry')
      : state.phase === 'success'
        ? getTamilPrompt('river-rescue', 'success')
        : state.phase === 'complete'
          ? getTamilPrompt('river-rescue', 'complete')
          : ''

  if (!sceneAudioRef.current && typeof window !== 'undefined') sceneAudioRef.current = createSceneAudioController(window)

  const shellState = useMemo(() => ({ ...state, stepIndex: state.pageIndex }), [state])

  useEffect(() => {
    narratorRef.current = createStoryNarrator({
      scope: window,
      loadAudio: async (lineId) => (await storyVoiceAPI.get(lineId)).data,
      preferNative: true,
    })
    return () => {
      narratorRef.current?.stop()
      sceneAudioRef.current?.stop()
    }
  }, [])

  useEffect(() => {
    const previous = previousScenePhaseRef.current
    previousScenePhaseRef.current = state.phase
    if (state.phase === previous || !sceneAudioActivatedRef.current || !preferences.soundEnabled) return
    if (state.phase === 'success') sceneAudioRef.current?.playEffect('water', { enabled: true, activated: true })
    if (state.phase === 'complete') sceneAudioRef.current?.playEffect('sparkle', { enabled: true, activated: true })
  }, [preferences.soundEnabled, state.phase])

  useEffect(() => {
    if (!preferences.soundEnabled) sceneAudioRef.current?.stop()
  }, [preferences.soundEnabled])

  const narrate = (storyPage = page) => {
    narratorRef.current?.stop()
    setIsSpeaking(true)
    dispatch({ type: 'NARRATION_STARTED' })
    const finish = () => {
      setIsSpeaking(false)
      dispatch({ type: 'NARRATION_ENDED' })
    }
    if (!preferences.soundEnabled || !preferences.spokenPrompts) {
      finish()
      return
    }
    narratorRef.current?.play({
      lineId: storyPage.lineId,
      text: storyPage.narration,
      voiceOptions: { guided: preferences.sessionPace === 'guided', enabled: true },
      onStart: () => setIsSpeaking(true),
      onEnd: finish,
      onError: finish,
    })
  }

  useEffect(() => {
    if (state.phase === 'narrating' && !isSpeaking) narrate(page)
    // page.id is the stable signal for a newly opened story page.
  }, [state.phase, page.id])

  useEffect(() => {
    if (!isRecording) {
      setAudioLevel(0)
      return undefined
    }
    let frame = 0
    const sample = () => {
      setAudioLevel(readAnalyserLevel(analyserRef.current))
      frame = window.requestAnimationFrame(sample)
    }
    frame = window.requestAnimationFrame(sample)
    return () => window.cancelAnimationFrame(frame)
  }, [analyserRef, isRecording])

  useEffect(() => {
    if (state.phase !== 'evaluating' || !audioBlob || submittedBlobRef.current === audioBlob) return
    submittedBlobRef.current = audioBlob
    dispatch({
      type: 'RESULT',
      result: {
        decision: 'UNSCORABLE',
        capability: 'story_word_assessment_not_supported',
        feedback_key: 'model_unavailable',
      },
    })
  }, [audioBlob, page.id, state.phase])

  useEffect(() => {
    if (!state.feedbackKey || !['ready', 'support', 'success', 'complete'].includes(state.phase)) return
    const feedbackId = `${page.id}:${state.feedbackKey}:${state.pageAttempts}`
    if (feedbackSpokenRef.current === feedbackId) return
    feedbackSpokenRef.current = feedbackId
    const text = FEEDBACK[state.feedbackKey]
    if (!text || !preferences.soundEnabled) return
    setIsSpeaking(true)
    narratorRef.current?.play({
      lineId: state.feedbackKey,
      text,
      voiceOptions: { guided: preferences.sessionPace === 'guided', enabled: true },
      onStart: () => setIsSpeaking(true),
      onEnd: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
    })
  }, [page.id, preferences.sessionPace, preferences.soundEnabled, state.feedbackKey, state.pageAttempts, state.phase])

  useEffect(() => {
    if (state.phase !== 'walking') return undefined
    setWalkingProgress(0)
    const startedAt = performance.now()
    const timer = window.setInterval(() => {
      const progress = Math.min(1, (performance.now() - startedAt) / 1200)
      setWalkingProgress(progress)
      if (progress >= 1) {
        window.clearInterval(timer)
        setWalkingProgress(0)
        resetRecording()
        submittedBlobRef.current = null
        dispatch({ type: 'WALK_FINISHED' })
      }
    }, 40)
    return () => window.clearInterval(timer)
  }, [resetRecording, state.phase])

  useEffect(() => {
    if (state.phase !== 'complete' || reportSentRef.current) return
    reportSentRef.current = true
    interactiveSessionsAPI.create(buildKaviStoryReport({ state, completedAt: Date.now() })).catch(() => {})
  }, [state])

  useEffect(() => () => {
    narratorRef.current?.stop()
    resetRecording()
  }, [resetRecording])

  const beginStory = () => {
    sceneAudioActivatedRef.current = true
    dispatch({ type: 'START', startedAt: Date.now() })
  }

  const beginListening = async () => {
    sceneAudioActivatedRef.current = true
    narratorRef.current?.stop()
    resetRecording()
    submittedBlobRef.current = null
    const allowed = await startRecording('ta-IN', { speechRecognition: true, repeatRecognized: false })
    if (allowed) dispatch({ type: 'LISTEN' })
    else {
      dispatch({ type: 'LISTEN' })
      dispatch({ type: 'EVALUATE' })
      dispatch({ type: 'RESULT', result: { capability: 'model_unavailable', feedback_key: 'model_unavailable' } })
    }
  }

  const finishListening = () => {
    stopRecording()
    dispatch({ type: 'EVALUATE' })
  }

  const resetStory = () => {
    narratorRef.current?.stop()
    resetRecording()
    submittedBlobRef.current = null
    reportSentRef.current = false
    sceneAudioRef.current?.stop()
    sceneAudioActivatedRef.current = false
    dispatch({ type: 'RESET' })
  }

  const message = state.phase === 'intro'
    ? 'வணக்கம்! நான் கவி. ஐந்து சொல் மந்திரங்களுடன் பாலத்தைக் கடக்கலாமா?'
    : FEEDBACK[state.feedbackKey] || page.narration

  return (
    <InteractiveSessionShell
      title="கவியின் பாலப் பயணம்"
      subtitle="ஐந்து படிகளில் தமிழ் பேசிப் பழகலாம்"
      state={shellState}
      steps={KAVI_STORY_PAGES.map((storyPage) => ({ id: storyPage.id, label: storyPage.target }))}
      labels={TAMIL_SHELL_LABELS}
    >
      <div className="storybook-layout" data-testid="kavi-storybook">
        <KaviStorybookScene
          pageIndex={state.pageIndex}
          mood={moodFor(state.phase, isSpeaking)}
          message={message}
          audioLevel={audioLevel}
          motionLevel={preferences.motionLevel}
          walkingProgress={walkingProgress}
          picture={page.picture}
          pictureAlt={page.pictureAlt}
          effectProfile={effectProfile}
        />

        <section className="storybook-card" aria-live="polite">
          <ol className="storybook-progress" data-testid="kavi-progress" aria-label="கதையின் ஐந்து படிகள்">
            {KAVI_STORY_PAGES.map((storyPage, index) => (
              <li key={storyPage.id} data-state={index < state.pageIndex ? 'done' : index === state.pageIndex ? 'current' : 'next'}>
                <span>{index + 1}</span><small>{storyPage.target}</small>
              </li>
            ))}
          </ol>

          <div className="storybook-copy">
            <span className="storybook-kicker"><BookOpen aria-hidden="true" /> பக்கம் {state.pageIndex + 1} / 5</span>
            {state.phase === 'intro' ? (
              <>
                <h2>வணக்கம், குட்டி நண்பரே!</h2>
                <p>{message}</p>
              </>
            ) : (
              <>
                <p>{message}</p>
                <div className="storybook-target" aria-label={`சொல்ல வேண்டியது: ${page.target}`}>{page.target}</div>
                {state.phase === 'support' ? <p className="storybook-help"><HelpCircle aria-hidden="true" /> {page.help}</p> : null}
              </>
            )}
          </div>

          <div className="storybook-actions">
            <TamilStatus label={animationPrompt} />
            {state.phase === 'intro' ? <button className="storybook-button storybook-button--primary" type="button" onClick={beginStory}><Sparkles aria-hidden="true" /> கதையைத் தொடங்கலாம்</button> : null}
            {state.phase === 'narrating' ? <button className="storybook-button" type="button" disabled><Volume2 aria-hidden="true" /> கவி கதை சொல்கிறான்...</button> : null}
            {state.phase === 'ready' ? <>
              <button className="storybook-button storybook-button--primary" type="button" onClick={beginListening}><Mic aria-hidden="true" /> சொல்லத் தொடங்கலாம்</button>
              <button className="storybook-button" type="button" onClick={() => narrate(page)}><Volume2 aria-hidden="true" /> மீண்டும் கேட்கலாம்</button>
            </> : null}
            {state.phase === 'listening' ? <button className="storybook-button storybook-button--stop" type="button" onClick={finishListening}><Square aria-hidden="true" /> முடித்தேன்</button> : null}
            {state.phase === 'evaluating' ? <button className="storybook-button" type="button" disabled><Ear aria-hidden="true" /> கவி கேட்டுப் பார்க்கிறான்...</button> : null}
            {state.phase === 'support' ? <>
              <button className="storybook-button storybook-button--primary" type="button" onClick={() => dispatch({ type: 'USE_HELP' })}><HelpCircle aria-hidden="true" /> கவியுடன் சேர்ந்து சொல்லலாம்</button>
              <button className="storybook-button" type="button" onClick={beginListening}><Mic aria-hidden="true" /> மீண்டும் முயலலாம்</button>
            </> : null}
            {state.phase === 'success' ? <button className="storybook-button storybook-button--primary" type="button" onClick={() => dispatch({ type: 'NEXT' })}><Sparkles aria-hidden="true" /> கவியுடன் நடக்கலாம்</button> : null}
            {state.phase === 'walking' ? <button className="storybook-button" type="button" disabled>கவி பாலத்தை நோக்கி நடக்கிறான்...</button> : null}
            {state.phase === 'complete' ? <button className="storybook-button storybook-button--primary" type="button" onClick={resetStory}><RotateCcw aria-hidden="true" /> கதையை மீண்டும் விளையாடலாம்</button> : null}
          </div>
        </section>
      </div>
    </InteractiveSessionShell>
  )
}

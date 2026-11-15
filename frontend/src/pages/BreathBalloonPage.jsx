import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { ArrowRight, Gauge, Hand, Mic, RotateCcw, ShieldCheck, Wind } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import BalloonScene from '../components/interactive/BalloonScene'
import ChildFeedback from '../components/interactive/ChildFeedback'
import InteractiveSessionShell from '../components/interactive/InteractiveSessionShell'
import { TamilStatus } from '../components/interactive/SceneEffects'
import { BREATH_BALLOON_ACTIVITY, createBreathBalloonReport } from '../features/arcade/breathBalloonActivity'
import { LETTER_FLIGHT_ROUNDS, findNewlyCrossedLetters, speakCuteLetterSound } from '../features/arcade/letterFlight'
import { getBreathVisualState, getEffectProfile, getTamilPrompt } from '../features/interactive/animationPresentation'
import { createNoiseCalibrator, normalizeAudioLevel, readAnalyserLevel, scoreTargetControl } from '../features/interactive/audioLevel'
import { createSceneAudioController } from '../features/interactive/sceneAudio'
import { createSession, sessionReducer } from '../features/interactive/sessionEngine'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { gamesAPI, interactiveSessionsAPI } from '../services/api'
import { useInteractionSettingsStore } from '../store/interactionSettingsStore'

const PASS_SCORE = 40

export default function BreathBalloonPage() {
  const navigate = useNavigate()
  const { preferences } = useInteractionSettingsStore()
  const [session, dispatch] = useReducer(sessionReducer, BREATH_BALLOON_ACTIVITY, createSession)
  const [mode, setMode] = useState('intro')
  const [level, setLevel] = useState(0)
  const [noiseFloor, setNoiseFloor] = useState(0.05)
  const [scores, setScores] = useState([])
  const [pendingScore, setPendingScore] = useState(null)
  const [demoMode, setDemoMode] = useState(false)
  const [permissionError, setPermissionError] = useState(false)
  const [crossedLetterIds, setCrossedLetterIds] = useState([])
  const [lastCrossedLetter, setLastCrossedLetter] = useState(null)
  const calibratorRef = useRef(createNoiseCalibrator())
  const phaseStartedRef = useRef(0)
  const samplesRef = useRef([])
  const attemptsRef = useRef(0)
  const assistanceRef = useRef({ independent: 0, verbal_prompt: 0, visual_prompt: 0, modelled: 0, skipped: 0 })
  const startedAtRef = useRef(Date.now())
  const completingRef = useRef(false)
  const previousFlightLevelRef = useRef(0)
  const crossedLetterIdsRef = useRef(new Set())
  const audioActivatedRef = useRef(false)
  const sceneAudioRef = useRef(null)
  const { isRecording, analyserRef, startRecording, stopRecording, resetRecording } = useAudioRecorder()
  const step = BREATH_BALLOON_ACTIVITY.steps[session.stepIndex] || BREATH_BALLOON_ACTIVITY.steps.at(-1)
  const letterObstacles = LETTER_FLIGHT_ROUNDS[session.stepIndex] || LETTER_FLIGHT_ROUNDS.at(-1)
  const visualState = getBreathVisualState({ mode, level, target: step.target })
  const effectProfile = getEffectProfile(preferences)
  const tamilPrompt = getTamilPrompt('breath-balloon', visualState)

  if (!sceneAudioRef.current && typeof window !== 'undefined') sceneAudioRef.current = createSceneAudioController(window)

  useEffect(() => () => resetRecording(), [resetRecording])

  useEffect(() => () => sceneAudioRef.current?.stop(), [])

  useEffect(() => {
    if (!preferences.soundEnabled) sceneAudioRef.current?.stop()
  }, [preferences.soundEnabled])

  useEffect(() => {
    if (!audioActivatedRef.current || !tamilPrompt || !['too-weak', 'too-strong', 'success', 'complete'].includes(visualState)) return
    sceneAudioRef.current?.speakTamil(tamilPrompt, {
      enabled: preferences.soundEnabled && preferences.spokenPrompts,
      activated: true,
    })
    if (visualState === 'success') sceneAudioRef.current?.playEffect('success', { enabled: preferences.soundEnabled, activated: true })
    if (visualState === 'complete') sceneAudioRef.current?.playEffect('sparkle', { enabled: preferences.soundEnabled, activated: true })
  }, [preferences.soundEnabled, preferences.spokenPrompts, tamilPrompt, visualState])

  useEffect(() => {
    if (mode !== 'playing') return
    const newlyCrossed = findNewlyCrossedLetters({
      previousLevel: previousFlightLevelRef.current,
      currentLevel: level,
      obstacles: letterObstacles,
      crossedIds: crossedLetterIdsRef.current,
    })
    for (const obstacle of newlyCrossed) {
      crossedLetterIdsRef.current.add(obstacle.id)
      setLastCrossedLetter(obstacle)
      if (preferences.soundEnabled) speakCuteLetterSound(window, obstacle)
    }
    if (newlyCrossed.length) setCrossedLetterIds([...crossedLetterIdsRef.current])
    previousFlightLevelRef.current = level
  }, [letterObstacles, level, mode, preferences.soundEnabled])

  const beginCalibration = async () => {
    audioActivatedRef.current = true
    sceneAudioRef.current?.speakTamil(getTamilPrompt('breath-balloon', 'intro'), {
      enabled: preferences.soundEnabled && preferences.spokenPrompts,
      activated: true,
    })
    setPermissionError(false)
    setMode('calibrating')
    calibratorRef.current.reset()
    phaseStartedRef.current = performance.now()
    dispatch({ type: 'START', at: Date.now() })
    const allowed = await startRecording('en-IN', { speechRecognition: false })
    if (!allowed) {
      setPermissionError(true)
      setMode('permission')
      dispatch({ type: 'CAPABILITY_ERROR', capability: 'microphone', message: 'Microphone permission was not available.', at: Date.now() })
    }
  }

  useEffect(() => {
    if (mode !== 'calibrating' || !isRecording) return undefined
    const timer = window.setInterval(() => {
      const raw = Math.min(1, readAnalyserLevel(analyserRef.current) * 2.4)
      const elapsed = performance.now() - phaseStartedRef.current
      setLevel(raw)
      const status = calibratorRef.current.add(raw, elapsed)
      if (status.complete) {
        setNoiseFloor(Math.min(0.35, calibratorRef.current.result()))
        stopRecording()
        setLevel(0)
        setMode('ready')
        dispatch({ type: 'PROMPT_FINISHED', at: Date.now() })
      }
    }, 70)
    return () => window.clearInterval(timer)
  }, [analyserRef, isRecording, mode, stopRecording])

  const finishRound = useCallback(() => {
    if (completingRef.current || mode !== 'playing') return
    completingRef.current = true
    stopRecording()
    const score = scoreTargetControl(samplesRef.current, step.target[0], step.target[1])
    setPendingScore(score)
    dispatch({ type: 'RESPONSE_CAPTURED', response: { score }, at: Date.now() })
    if (score >= PASS_SCORE) {
      dispatch({ type: 'EVALUATION_SUCCEEDED', assistance: 'independent', at: Date.now() })
      setMode('success')
    } else {
      dispatch({ type: 'EVALUATION_RETRY', at: Date.now() })
      setMode('support')
    }
    window.setTimeout(() => { completingRef.current = false }, 0)
  }, [mode, step.target, stopRecording])

  useEffect(() => {
    if (mode !== 'playing') return undefined
    const sampleTimer = window.setInterval(() => {
      const value = demoMode
        ? level
        : normalizeAudioLevel(Math.min(1, readAnalyserLevel(analyserRef.current) * 2.4), noiseFloor)
      samplesRef.current.push(value)
      if (!demoMode) setLevel(value)
    }, 70)
    const timeout = window.setTimeout(finishRound, step.timeoutMs)
    return () => {
      window.clearInterval(sampleTimer)
      window.clearTimeout(timeout)
    }
  }, [analyserRef, demoMode, finishRound, level, mode, noiseFloor, step.timeoutMs])

  const startRound = async () => {
    completingRef.current = false
    samplesRef.current = []
    setPendingScore(null)
    crossedLetterIdsRef.current = new Set()
    previousFlightLevelRef.current = 0
    setCrossedLetterIds([])
    setLastCrossedLetter(null)
    setLevel(demoMode ? 0.35 : 0)
    attemptsRef.current += 1
    dispatch({ type: 'BEGIN_ATTEMPT', at: Date.now() })
    if (!demoMode) {
      const allowed = await startRecording('en-IN', { speechRecognition: false })
      if (!allowed) {
        setPermissionError(true)
        setMode('permission')
        return
      }
    }
    setMode('playing')
  }

  const submitCompletion = (finalScores, finalAssistance) => {
    const completedAt = Date.now()
    const report = createBreathBalloonReport({
      startedAt: startedAtRef.current,
      completedAt,
      scores: finalScores,
      attempts: attemptsRef.current,
      assistance: finalAssistance,
      effortPoints: finalScores.length * 3,
    })
    interactiveSessionsAPI.create(report).catch(() => {})
    const average = Math.round(finalScores.reduce((sum, value) => sum + value, 0) / Math.max(1, finalScores.length))
    gamesAPI.submitScore({ game_slug: 'breath-balloon', score: average, accuracy: average, duration_sec: Math.round(report.duration_ms / 1000), level_reached: 3 }).catch(() => {})
  }

  const continueAfterResult = (supported = false) => {
    const score = Number(pendingScore) || 0
    const finalScores = [...scores, score]
    const finalAssistance = { ...assistanceRef.current }
    if (supported) {
      finalAssistance.visual_prompt += 1
      assistanceRef.current = finalAssistance
      dispatch({ type: 'USE_HINT', assistance: 'visual_prompt', at: Date.now() })
      dispatch({ type: 'EVALUATION_SUCCEEDED', assistance: null, at: Date.now() })
    } else {
      finalAssistance.independent += 1
      assistanceRef.current = finalAssistance
    }
    setScores(finalScores)
    dispatch({ type: 'NEXT_STEP', at: Date.now() })
    if (session.stepIndex >= BREATH_BALLOON_ACTIVITY.steps.length - 1) {
      submitCompletion(finalScores, finalAssistance)
      setMode('complete')
    } else {
      setMode('ready')
      setLevel(0)
    }
  }

  const useScreenControl = () => {
    audioActivatedRef.current = true
    resetRecording()
    setDemoMode(true)
    setPermissionError(false)
    setNoiseFloor(0)
    setMode('ready')
    dispatch({ type: 'RESET', at: Date.now() })
    dispatch({ type: 'START', at: Date.now() })
    dispatch({ type: 'PROMPT_FINISHED', at: Date.now() })
  }

  const restart = () => {
    resetRecording()
    dispatch({ type: 'RESET', at: Date.now() })
    startedAtRef.current = Date.now()
    attemptsRef.current = 0
    assistanceRef.current = { independent: 0, verbal_prompt: 0, visual_prompt: 0, modelled: 0, skipped: 0 }
    setScores([])
    setPendingScore(null)
    setDemoMode(false)
    setLevel(0)
    crossedLetterIdsRef.current = new Set()
    previousFlightLevelRef.current = 0
    setCrossedLetterIds([])
    setLastCrossedLetter(null)
    window.speechSynthesis?.cancel()
    sceneAudioRef.current?.stop()
    audioActivatedRef.current = false
    setMode('intro')
  }

  const exitActivity = () => {
    resetRecording()
    window.speechSynthesis?.cancel()
    sceneAudioRef.current?.stop()
    navigate('/play')
  }

  return (
    <InteractiveSessionShell title="Breath Balloon" subtitle="Keep the balloon inside the glowing zone" state={session} dispatch={dispatch} steps={BREATH_BALLOON_ACTIVITY.steps} onExit={exitActivity}>
      <div className="breath-game">
        {mode === 'intro' ? (
          <div className="breath-card breath-card--intro">
            <span className="breath-card__hero"><Wind aria-hidden="true" /></span>
            <ChildFeedback title={getTamilPrompt('breath-balloon', 'intro')} detail="Ready for a balloon adventure? First, stay quiet for two seconds so the game can learn the room sound." />
            <div className="breath-card__privacy"><ShieldCheck aria-hidden="true" /> Sound is used live and is not saved.</div>
            <button className="interactive-control interactive-primary-button breath-button" type="button" onClick={beginCalibration}><Mic aria-hidden="true" /> Check my microphone</button>
          </div>
        ) : null}

        {mode === 'calibrating' ? (
          <div className="breath-card">
            <span className="calibration-orb" style={{ '--sound-level': level }} aria-hidden="true" />
            <ChildFeedback kind="listening" title="Listening to the room" detail="Stay quiet for just two seconds." />
          </div>
        ) : null}

        {mode === 'permission' ? (
          <div className="breath-card">
            <span className="breath-card__hero breath-card__hero--soft"><Hand aria-hidden="true" /></span>
            <ChildFeedback kind="error" title="The microphone is off" detail="That is okay. Move the balloon with the screen control instead." />
            {permissionError ? <p className="breath-card__note">A grown-up can enable microphone permission later in browser settings.</p> : null}
            <div className="breath-actions">
              <button className="interactive-control interactive-primary-button breath-button" type="button" onClick={useScreenControl}><Gauge aria-hidden="true" /> Use screen control</button>
              <button className="interactive-control breath-button breath-button--quiet" type="button" onClick={() => navigate('/play')}>Back</button>
            </div>
          </div>
        ) : null}

        {['ready', 'playing', 'success', 'support'].includes(mode) ? (
          <div className="breath-play-area">
            <BalloonScene
              level={level}
              target={step.target}
              active={mode === 'playing'}
              score={['success', 'support'].includes(mode) ? pendingScore : undefined}
              obstacles={letterObstacles}
              crossedIds={crossedLetterIds}
              lastCrossed={lastCrossedLetter}
              visualState={visualState}
              motionLevel={preferences.motionLevel}
              effectProfile={effectProfile}
            />
            <TamilStatus label={tamilPrompt} />
            {demoMode && mode === 'playing' ? (
              <label className="breath-slider"><span>Move your balloon</span><input aria-label="Balloon voice level" type="range" min="0" max="100" value={Math.round(level * 100)} onChange={(event) => setLevel(Number(event.target.value) / 100)} /></label>
            ) : null}
            <div className="breath-controls">
              {mode === 'ready' ? <><ChildFeedback title={step.label} detail={`Round ${session.stepIndex + 1} of 3. Stay in the glowing zone.`} /><button className="interactive-control interactive-primary-button breath-button" type="button" onClick={startRound}>{demoMode ? <Gauge aria-hidden="true" /> : <Mic aria-hidden="true" />} Start round</button></> : null}
              {mode === 'playing' ? <><ChildFeedback kind="listening" title="Keep it steady" detail="You can stop when you are ready." /><button className="interactive-control breath-button breath-button--stop" type="button" onClick={finishRound}>Check my balloon</button></> : null}
              {mode === 'success' ? <><ChildFeedback kind="success" title="Beautiful control!" detail="Your balloon floated right through the steady zone." /><button className="interactive-control interactive-primary-button breath-button" type="button" onClick={() => continueAfterResult(false)}>Next round <ArrowRight aria-hidden="true" /></button></> : null}
              {mode === 'support' ? <><ChildFeedback kind="support" title="Nice brave try" detail="Try once more, or use the gentle guide and keep going." /><div className="breath-actions"><button className="interactive-control interactive-primary-button breath-button" type="button" onClick={startRound}><RotateCcw aria-hidden="true" /> Try again</button><button className="interactive-control breath-button breath-button--quiet" type="button" onClick={() => continueAfterResult(true)}>Keep going</button></div></> : null}
            </div>
          </div>
        ) : null}

        {mode === 'complete' ? (
          <div className="breath-card breath-card--complete">
            <BalloonScene
              level={1}
              target={step.target}
              visualState="complete"
              motionLevel={preferences.motionLevel}
              effectProfile={effectProfile}
              showMeter={false}
            />
            <ChildFeedback kind="success" title={getTamilPrompt('breath-balloon', 'complete')} detail={`Three balloons are flying! Best steady control: ${Math.max(...scores, 0)}%.`} />
            <div className="breath-actions"><button className="interactive-control interactive-primary-button breath-button" type="button" onClick={() => navigate('/play')}>Choose another adventure</button><button className="interactive-control breath-button breath-button--quiet" type="button" onClick={restart}><RotateCcw aria-hidden="true" /> Play again</button></div>
          </div>
        ) : null}
      </div>
    </InteractiveSessionShell>
  )
}

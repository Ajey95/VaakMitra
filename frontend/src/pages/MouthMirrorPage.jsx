import { useEffect, useReducer, useRef, useState } from 'react'
import { Camera, CameraOff, Check, Eye, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import ChildFeedback from '../components/interactive/ChildFeedback'
import InteractiveSessionShell from '../components/interactive/InteractiveSessionShell'
import MouthGuideOverlay from '../components/interactive/MouthGuideOverlay'
import { CelebrationLayer, TamilStatus } from '../components/interactive/SceneEffects'
import { getEffectProfile, getTamilPrompt } from '../features/interactive/animationPresentation'
import { createSceneAudioController } from '../features/interactive/sceneAudio'
import { classifyMouthTarget, createHoldTracker } from '../features/mouthMirror/mouthGeometry'
import { MOUTH_MIRROR_ACTIVITY, MOUTH_TARGETS } from '../features/mouthMirror/targets'
import { createSession, sessionReducer } from '../features/interactive/sessionEngine'
import { useFaceDetection } from '../hooks/useFaceDetection'
import { interactiveSessionsAPI } from '../services/api'
import { useInteractionSettingsStore } from '../store/interactionSettingsStore'

const EMPTY_ASSISTANCE = { independent: 0, verbal_prompt: 0, visual_prompt: 0, modelled: 0, skipped: 0 }

export default function MouthMirrorPage() {
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const holdRef = useRef(createHoldTracker(600))
  const lastFrameRef = useRef(performance.now())
  const startedAtRef = useRef(Date.now())
  const attemptsRef = useRef(0)
  const assistanceRef = useRef({ ...EMPTY_ASSISTANCE })
  const completedRef = useRef(false)
  const sceneAudioRef = useRef(null)
  const audioActivatedRef = useRef(false)
  const previousModeRef = useRef('gate')
  const [session, dispatch] = useReducer(sessionReducer, MOUTH_MIRROR_ACTIVITY, createSession)
  const [mode, setMode] = useState('gate')
  const [cameraError, setCameraError] = useState('')
  const [match, setMatch] = useState({ matched: false, cue: '', progress: 0 })
  const { preferences, updatePreference } = useInteractionSettingsStore()
  const { faceData, startDetection, stopDetection } = useFaceDetection(videoRef, canvasRef)
  const target = MOUTH_TARGETS[session.stepIndex] || MOUTH_TARGETS.at(-1)
  const effectProfile = getEffectProfile(preferences)
  const mirrorVisualState = mode === 'success'
    ? 'matched'
    : mode === 'camera' && faceData.faceDetected && match.progress > 0
      ? 'close'
      : mode === 'camera' && faceData.faceDetected
        ? 'retry'
        : mode === 'model'
          ? 'model'
          : 'waiting'

  if (!sceneAudioRef.current && typeof window !== 'undefined') sceneAudioRef.current = createSceneAudioController(window)

  const stopCamera = () => {
    stopDetection()
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
  }

  useEffect(() => () => {
    stopCamera()
    sceneAudioRef.current?.stop()
  }, [])

  useEffect(() => {
    const previous = previousModeRef.current
    previousModeRef.current = mode
    if (mode !== 'success' || previous === 'success' || !audioActivatedRef.current) return
    const prompt = getTamilPrompt('mouth-mirror', 'matched')
    sceneAudioRef.current?.speakTamil(prompt, { enabled: preferences.soundEnabled && preferences.spokenPrompts, activated: true })
    sceneAudioRef.current?.playEffect('sparkle', { enabled: preferences.soundEnabled, activated: true })
  }, [mode, preferences.soundEnabled, preferences.spokenPrompts])

  useEffect(() => {
    if (!preferences.soundEnabled) sceneAudioRef.current?.stop()
  }, [preferences.soundEnabled])

  useEffect(() => {
    if (mode !== 'camera' || !faceData.faceDetected || completedRef.current) {
      if (!faceData.faceDetected) {
        holdRef.current.reset()
        setMatch((current) => ({ ...current, matched: false, progress: 0 }))
      }
      return
    }
    const geometry = {
      mouthWidth: faceData.mouthWidth,
      mouthHeight: faceData.mouthHeight,
      mouthOpenRatio: faceData.mouthOpenRatio,
    }
    const result = classifyMouthTarget(geometry, target)
    const now = performance.now()
    const hold = holdRef.current.update(result.matched, Math.min(100, now - lastFrameRef.current))
    lastFrameRef.current = now
    setMatch({ ...result, progress: hold.progress })
    if (hold.complete) {
      completedRef.current = true
      setMode('success')
      dispatch({ type: 'BEGIN_ATTEMPT', at: Date.now() })
      dispatch({ type: 'RESPONSE_CAPTURED', response: { matched: true }, at: Date.now() })
      dispatch({ type: 'EVALUATION_SUCCEEDED', assistance: 'independent', at: Date.now() })
    }
  }, [faceData, mode, target])

  const startCamera = async () => {
    audioActivatedRef.current = true
    setCameraError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.onloadedmetadata = () => {
          const width = videoRef.current?.videoWidth || 640
          const height = videoRef.current?.videoHeight || 480
          if (canvasRef.current) {
            canvasRef.current.width = width
            canvasRef.current.height = height
          }
          startDetection()
        }
      }
      updatePreference('cameraEnabled', true)
      holdRef.current.reset()
      completedRef.current = false
      lastFrameRef.current = performance.now()
      setMode('camera')
      dispatch({ type: 'START', at: Date.now() })
      dispatch({ type: 'PROMPT_FINISHED', at: Date.now() })
    } catch {
      setCameraError('Camera permission is unavailable. Model-only practice still works.')
      setMode('gate')
    }
  }

  const useModelOnly = () => {
    audioActivatedRef.current = true
    stopCamera()
    holdRef.current.reset()
    completedRef.current = false
    setMode('model')
    dispatch({ type: 'START', at: Date.now() })
    dispatch({ type: 'PROMPT_FINISHED', at: Date.now() })
  }

  const submitReport = (assistance) => {
    const now = Date.now()
    interactiveSessionsAPI.create({
      activity_id: 'mouth-mirror',
      activity_type: 'mouth_mirror',
      started_at: new Date(startedAtRef.current).toISOString(),
      completed_at: new Date(now).toISOString(),
      communication_turns: MOUTH_TARGETS.length,
      successful_turns: MOUTH_TARGETS.length,
      attempts: attemptsRef.current,
      assistance_counts: assistance,
      duration_ms: Math.min(3_600_000, now - startedAtRef.current),
      effort_points: MOUTH_TARGETS.length * 2,
    }).catch(() => {})
  }

  const advance = (assistance) => {
    attemptsRef.current += 1
    assistanceRef.current[assistance] += 1
    if (mode === 'model') {
      dispatch({ type: 'BEGIN_ATTEMPT', at: Date.now() })
      dispatch({ type: 'RESPONSE_CAPTURED', response: { caregiverConfirmed: true }, at: Date.now() })
      dispatch({ type: 'EVALUATION_SUCCEEDED', assistance, at: Date.now() })
    }
    if (session.stepIndex >= MOUTH_TARGETS.length - 1) {
      dispatch({ type: 'COMPLETE', at: Date.now() })
      stopCamera()
      submitReport({ ...assistanceRef.current })
      setMode('complete')
      return
    }
    dispatch({ type: 'NEXT_STEP', at: Date.now() })
    holdRef.current.reset()
    completedRef.current = false
    setMatch({ matched: false, cue: '', progress: 0 })
    setMode(streamRef.current ? 'camera' : 'model')
  }

  return (
    <InteractiveSessionShell title="Mouth Mirror" subtitle="Look, copy, and hold each mouth shape" state={session} dispatch={dispatch} steps={MOUTH_MIRROR_ACTIVITY.steps}>
      <div className="mirror-wrap">
        {mode === 'gate' ? (
          <div className="mirror-gate">
            <span className="mirror-gate__icon"><Eye aria-hidden="true" /></span>
            <ChildFeedback title="Choose how to practise" detail="A grown-up can turn on a private live mirror, or practise with the model only." />
            <div className="mirror-privacy"><ShieldCheck aria-hidden="true" /><span><strong>Local and temporary</strong> Camera frames stay on this device and are never recorded or uploaded.</span></div>
            {cameraError ? <p className="mirror-error" role="alert">{cameraError}</p> : null}
            <div className="mirror-actions">
              <button className="interactive-control mirror-button mirror-button--primary" type="button" onClick={startCamera}><Camera aria-hidden="true" /> {preferences.cameraEnabled ? 'Start private mirror' : 'Allow camera this time'}</button>
              <button className="interactive-control mirror-button mirror-button--quiet" type="button" onClick={useModelOnly}><CameraOff aria-hidden="true" /> Model only</button>
            </div>
          </div>
        ) : null}

        {['camera', 'model', 'success'].includes(mode) ? (
          <div className={`mirror-stage ${mode === 'model' ? 'is-model-only' : ''}`}>
            <MouthGuideOverlay
              target={target}
              matched={match.matched || mode === 'success'}
              progress={mode === 'success' ? 1 : match.progress}
              visualState={mirrorVisualState}
              motionLevel={preferences.motionLevel}
            />
            {mode === 'success' ? <CelebrationLayer variant="mirror-stars" state="matched" effectProfile={effectProfile} /> : null}
            {mode !== 'model' ? (
              <div className="mirror-camera">
                <video ref={videoRef} autoPlay muted playsInline />
                <canvas ref={canvasRef} aria-hidden="true" />
                <span className="mirror-camera__live"><i /> Live on this device · not recorded</span>
                {!faceData.faceDetected && mode === 'camera' ? <span className="mirror-camera__tip">Move your face into the mirror</span> : null}
              </div>
            ) : (
              <div className="mirror-model-message"><CameraOff aria-hidden="true" /><strong>No camera is running</strong><span>Copy the friendly model at your own pace.</span></div>
            )}
            <div className="mirror-feedback">
              {mode === 'success' ? <ChildFeedback kind="success" title={getTamilPrompt('mouth-mirror', 'matched')} detail="Shape held! That mouth movement was steady." /> : <ChildFeedback title={target.label} detail={mode === 'camera' ? (faceData.faceDetected ? match.cue : 'The mirror is waiting for your face.') : 'A grown-up can tap when the shape is ready.'} />}
              <TamilStatus label={mirrorVisualState === 'retry' ? getTamilPrompt('mouth-mirror', 'retry') : mirrorVisualState === 'matched' ? getTamilPrompt('mouth-mirror', 'matched') : ''} />
              <div className="mirror-actions">
                {mode === 'success' ? <button className="interactive-control mirror-button mirror-button--primary" type="button" onClick={() => advance('independent')}><Check aria-hidden="true" /> Next shape</button> : null}
                {mode === 'model' ? <button className="interactive-control mirror-button mirror-button--primary" type="button" onClick={() => advance('modelled')}><Check aria-hidden="true" /> I copied it</button> : null}
                {mode === 'camera' ? <button className="interactive-control mirror-button mirror-button--quiet" type="button" onClick={useModelOnly}><CameraOff aria-hidden="true" /> Use model only</button> : null}
              </div>
            </div>
          </div>
        ) : null}

        {mode === 'complete' ? (
          <div className="mirror-gate mirror-gate--complete">
            <span className="mirror-gate__icon">5</span>
            <div className="mirror-complete-stars" aria-hidden="true"><i>★</i><i>★</i><i>★</i><i>★</i><i>★</i></div>
            <CelebrationLayer variant="mirror-stars" state="complete" effectProfile={effectProfile} />
            <ChildFeedback kind="success" title="Mouth Mirror complete!" detail="You copied five useful speech shapes. No camera frames were saved." />
            <button className="interactive-control mirror-button mirror-button--primary" type="button" onClick={() => navigate('/play')}>Choose another adventure</button>
          </div>
        ) : null}
      </div>
    </InteractiveSessionShell>
  )
}

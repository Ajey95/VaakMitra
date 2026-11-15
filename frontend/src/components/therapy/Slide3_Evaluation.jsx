import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Mic, Square, Volume2 } from 'lucide-react'
import { useAudioRecorder } from '../../hooks/useAudioRecorder'
import { convertAudioBlobToWav } from '../../utils/audioWav'
import { wordAssessmentOutcome } from '../../features/wordAssessment/outcome'

function VolumeMeter({ level }) {
  const pct = Math.min(100, Math.round(level * 140))
  return <div className="flex items-center gap-3 text-neutral-500 text-sm">
    <Volume2 className="w-4 h-4" aria-hidden="true" />
    <div className="flex-1 h-3 bg-neutral-200 rounded-full overflow-hidden">
      <div className="h-full bg-gradient-to-r from-primary to-accent" style={{ width: `${pct}%` }} />
    </div>
    <span>{pct < 25 ? 'Speak gently' : pct > 80 ? 'A little softer' : 'Listening'}</span>
  </div>
}

export default function Slide3_Evaluation({ snapshot, phase, result, onSubmit, onCaptureState }) {
  const [micLevel, setMicLevel] = useState(0)
  const [localError, setLocalError] = useState(null)
  const submittingRef = useRef(false)
  const submittedBlobRef = useRef(null)
  const { isRecording, audioBlob, analyserRef, startRecording, stopRecording, resetRecording } = useAudioRecorder()
  const active = phase === 'active' && snapshot?.status === 'active'
  const outcome = result ? wordAssessmentOutcome(result) : null
  const word = snapshot?.target_word || ''

  useEffect(() => {
    if (!isRecording) { setMicLevel(0); return undefined }
    const timer = window.setInterval(() => {
      const analyser = analyserRef.current
      if (!analyser) return
      const values = new Uint8Array(analyser.frequencyBinCount)
      analyser.getByteFrequencyData(values)
      setMicLevel(values.reduce((sum, value) => sum + value, 0) / values.length / 255)
    }, 80)
    return () => window.clearInterval(timer)
  }, [analyserRef, isRecording])

  useEffect(() => {
    onCaptureState?.({ isRecording, audioLevel: micLevel })
  }, [isRecording, micLevel, onCaptureState])

  // SES-003, UX-002: transition/unmount discards capture; no browser transcript or TTS is started.
  useEffect(() => {
    if (!active) resetRecording()
  }, [active, resetRecording])
  useEffect(() => {
    resetRecording()
    submittedBlobRef.current = null
    setLocalError(null)
  }, [snapshot?.word_id, resetRecording])
  useEffect(() => () => resetRecording(), [resetRecording])

  const record = async () => {
    if (!active) return
    if (isRecording) { stopRecording(); return }
    resetRecording()
    submittedBlobRef.current = null
    setLocalError(null)
    await startRecording('ta-IN', { speechRecognition: false, repeatRecognized: false })
  }

  const submit = async () => {
    if (!active || !audioBlob || submittingRef.current || submittedBlobRef.current === audioBlob) return
    submittingRef.current = true
    submittedBlobRef.current = audioBlob
    setLocalError(null)
    try {
      const wav = await convertAudioBlobToWav(audioBlob)
      if (wav.size > 8 * 1024 * 1024 - 4096) throw new Error('This recording is too long. Please make a shorter one.')
      await onSubmit(wav)
    } catch (error) {
      setLocalError(error?.message || 'The word check is unavailable. Please ask a grown-up for help.')
    } finally {
      submittingRef.current = false
    }
  }

  return <div className="h-full flex items-center justify-center p-6 md:p-8 relative">
    <div className="max-w-7xl w-full">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-6">
        <h2 className="text-3xl md:text-4xl font-bold mb-2 text-neutral-700">{phase === 'paused' ? 'Practice paused' : phase === 'ended' ? 'Session ended' : 'Your turn! Say the word 🎤'}</h2>
        <div className="inline-flex items-center gap-3 bg-white rounded-2xl px-6 py-3 shadow-md border border-neutral-100">
          <span className="tamil-letter text-4xl font-bold gradient-text">{word}</span>
        </div>
      </motion.div>
      <div className="grid lg:grid-cols-2 gap-6">
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="bg-white rounded-3xl shadow-2xl p-6">
          <div className="relative aspect-video bg-gradient-to-br from-neutral-900 to-indigo-950 rounded-2xl overflow-hidden mb-4 flex items-center justify-center">
            <span className="absolute top-4 left-4 bg-black/40 backdrop-blur px-4 py-2 rounded-full text-white text-sm">🔒 Camera is not used for word scoring</span>
            <div className="text-white/70 text-5xl" aria-hidden="true">🎙️</div>
            {isRecording && <span className="absolute bottom-3 left-3 right-3 rounded-xl bg-coral-500 text-white text-center py-2" role="status">🎤 Listening now</span>}
          </div>
          <div className="flex flex-col items-center py-2">
            {active && <motion.button onClick={record} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
              className={`w-[72px] h-[72px] rounded-full flex items-center justify-center text-white shadow-lg ${isRecording ? 'bg-coral-500' : 'bg-gradient-to-br from-primary to-secondary'}`}
              aria-label={isRecording ? 'Stop recording' : 'Start recording'}>
              {isRecording ? <Square className="w-7 h-7 fill-white" /> : <Mic className="w-8 h-8" />}
            </motion.button>}
            <p className="text-sm font-semibold text-center mt-3 min-h-[20px] text-neutral-600" role="status">
              {phase === 'paused' ? snapshot?.pause_reason === 'user_pause' ? 'Your break is here. Continue when you feel ready.' : 'This session is paused. A grown-up can help continue.' : phase === 'processing' ? 'Checking the word locally…' : phase === 'ended' ? 'This session has ended.' : isRecording ? 'Listening… you can stop the recording at any time.' : audioBlob ? 'Recording ready to check' : 'Tap the microphone when you are ready.'}
            </p>
          </div>
          {isRecording && <VolumeMeter level={micLevel} />}
          {active && audioBlob && !isRecording && <div className="flex gap-3 mt-4">
            <button onClick={submit} disabled={submittedBlobRef.current === audioBlob} className="flex-1 bg-accent-500 hover:bg-accent-600 text-white py-3 rounded-xl font-semibold disabled:opacity-50">Check word</button>
            <button onClick={() => { resetRecording(); submittedBlobRef.current = null }} className="px-5 rounded-xl border-2 border-neutral-200 text-neutral-700">Record again</button>
          </div>}
          {localError && <p className="text-coral-600 text-sm mt-3" role="alert">{localError}</p>}
          <p className="text-xs text-neutral-500 text-center mt-5">Attempt {Math.max(1, (snapshot?.attempt_count || 0) + 1)} · Your therapist sets the practice limit.</p>
        </motion.div>
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="bg-white rounded-3xl shadow-2xl p-6">
          <h3 className="text-xl font-bold mb-5">Private Word Check</h3>
          {outcome ? <div className={`rounded-2xl p-4 mb-5 border-2 ${outcome.kind === 'success' ? 'bg-accent-50 border-accent-300' : outcome.kind === 'retry' ? 'bg-amber-50 border-amber-300' : 'bg-secondary-50 border-secondary-300'}`} role="status">
            <p className="font-bold text-lg text-neutral-800">{outcome.heading}</p>
            <p className="text-sm text-neutral-600">{outcome.detail}</p>
          </div> : <p className="text-neutral-500 py-10">{active ? 'Record your word when you are ready. You can pause or stop at any time.' : 'No word judgement is being made now.'}</p>}
          <div className="rounded-2xl bg-neutral-50 border border-neutral-200 p-4 text-sm text-neutral-600">
            VaakMitra checks only your therapist-assigned Tamil word. There is no camera judgement, browser transcript, or child-facing percentage.
          </div>
        </motion.div>
      </div>
    </div>
  </div>
}

import { useState } from 'react'
import { Hand, Square } from 'lucide-react'
import Slide3_Evaluation from './Slide3_Evaluation'
import InteractiveAvatar from './InteractiveAvatar'
import { useAuthStore } from '../../store/authStore'
import { avatarById } from '../../features/avatar/avatarCatalog'
import { useAvatarPreference } from '../../features/avatar/useAvatarPreference'

function avatarPresentation(phase, result, captureActive) {
  if (phase === 'processing') return { phase: 'PROCESSING', message: 'I am checking this whole-word attempt locally.' }
  if (phase === 'paused') return { phase: 'BREAK', message: 'Take the time you need. The microphone is off.' }
  if (phase === 'ended') return { phase: 'BREAK', message: 'This practice session has ended.' }
  if (captureActive) return { phase: 'LISTENING', message: 'I am listening to one whole-word attempt.' }
  if (result?.decision === 'PASS') return { phase: 'PRAISE', message: 'Well done. Let’s continue with the assigned plan.' }
  if (result?.decision === 'RETRY') return { phase: 'COACH', message: 'Good try. Listen and say the whole word once more.' }
  if (result?.decision === 'UNSCORABLE') return { phase: 'ERROR', message: 'I could not check that recording. Let’s try a fresh one.' }
  return { phase: 'IDLE', message: 'When you are ready, use the microphone for one whole-word attempt.' }
}

// UX-003/SES-007: the first child safety action silences capture before any choice UI.
export default function SlideManager({ snapshot, phase, reason, result, summary, onPause, onResume, onStop, onSubmit }) {
  const user = useAuthStore((state) => state.user)
  const avatarPreference = useAvatarPreference(user?.child_id || user?.childId || user?.id || user?._id || '')
  const avatarName = avatarById(avatarPreference.avatarId).name
  const [choiceOpen, setChoiceOpen] = useState(false)
  const [captureState, setCaptureState] = useState({ isRecording: false, audioLevel: 0 })
  const canStop = snapshot?.session_id && !['ended', 'complete'].includes(snapshot.status)
  const voluntaryBreak = phase === 'paused' && snapshot?.pause_reason === 'user_pause'
  const avatar = avatarPresentation(phase, result, captureState.isRecording)
  const pressSafety = () => {
    onPause()
    setChoiceOpen(true)
  }
  return <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-green-50 to-teal-50">
    <div className="bg-white/70 backdrop-blur-xl shadow-sm border-b border-white/60 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
        <div className="inline-flex items-center gap-2 bg-primary/10 px-3.5 py-1.5 rounded-full">
          <span className="tamil-letter font-bold text-primary text-lg leading-none">{snapshot?.target_word}</span>
          <span className="font-semibold text-primary text-sm hidden sm:inline">Therapist-assigned word</span>
        </div>
        <span className="text-sm font-bold text-emerald-700 hidden sm:inline">Your Turn!</span>
        <div className="flex items-center gap-2">
          {['active', 'processing'].includes(phase) && <button onClick={pressSafety} aria-label="Break or stop" className="inline-flex min-h-12 items-center gap-2 px-5 py-3 rounded-2xl bg-red-600 hover:bg-red-700 focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-red-800 text-white font-bold text-base shadow-md"><Hand className="w-5 h-5" aria-hidden="true" /> Break / Stop</button>}
          {canStop && ['paused', 'blocked'].includes(phase) && !choiceOpen && <button onClick={onStop} aria-label="End session" className="inline-flex min-h-12 items-center gap-2 px-5 py-3 rounded-2xl bg-red-600 hover:bg-red-700 text-white font-bold"><Square className="w-5 h-5" aria-hidden="true" /> End session</button>}
        </div>
      </div>
    </div>
    {choiceOpen && canStop && <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/60 p-5" role="dialog" aria-modal="true" aria-label="Break or stop choices">
      <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl text-center">
        <h2 className="text-2xl font-bold text-neutral-900">You can take a break</h2>
        <p className="mt-2 text-neutral-600">The microphone is off.</p>
        <div className="mt-6 grid gap-3">
          <button type="button" autoFocus onClick={() => setChoiceOpen(false)} className="min-h-14 rounded-2xl bg-emerald-100 text-emerald-900 text-lg font-bold focus-visible:outline focus-visible:outline-4 focus-visible:outline-emerald-600">Take a break</button>
          <button type="button" onClick={() => { setChoiceOpen(false); onStop() }} className="min-h-14 rounded-2xl bg-red-600 text-white text-lg font-bold focus-visible:outline focus-visible:outline-4 focus-visible:outline-red-800">End session</button>
        </div>
      </div>
    </div>}
    {voluntaryBreak && !choiceOpen && <div className="mx-auto max-w-xl p-4 text-center" role="status">
      <p className="font-semibold text-neutral-800">Take the time you need.</p>
      {reason === 'completed_break_required' && <p className="mt-1 text-amber-800">The break is still going. You can continue in a moment.</p>}
      <button type="button" onClick={onResume} className="mt-3 min-h-12 rounded-2xl bg-emerald-700 px-6 py-3 text-white font-bold">Continue when ready</button>
    </div>}
    <div className="training-session-layout" data-testid="training-session-layout">
      <section className="training-session-content">
        <Slide3_Evaluation snapshot={snapshot} phase={phase} result={result} onSubmit={onSubmit} onCaptureState={setCaptureState} />
        {phase === 'ended' && <div className="max-w-3xl mx-auto bg-white rounded-3xl shadow-lg p-6 mb-8 text-center" role="status">
          <h3 className="text-xl font-bold">Session ended</h3>
          <p className="text-neutral-600">Thank you for practising. You can take a break now.</p>
          {summary && <p className="text-xs text-neutral-500 mt-2">Your practice record is available in your reports. Sharing with a therapist requires separate permission.</p>}
        </div>}
      </section>
      <aside className="training-pippin word-session-companion" aria-label="Practice companion">
        <header className="training-pippin__header"><span>{avatarName}</span><strong>Practice companion</strong></header>
        <div className="p-5 text-center">
          <InteractiveAvatar compact phase={avatar.phase} message={avatar.message} targetWord={snapshot?.target_word}
            audioLevel={captureState.audioLevel} active={['active', 'processing'].includes(phase)} onStop={pressSafety} scopeLabel="GUARDED WORD PRACTICE" avatarPreference={avatarPreference} />
          <p className="text-xs text-neutral-500 mt-4">Approved local voice prompts are not installed in this browser session.</p>
        </div>
      </aside>
    </div>
  </div>
}

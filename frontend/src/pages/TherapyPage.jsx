import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { therapyAPI } from '../services/api'
import { canonicalWordClient } from '../services/api'
import SlideManager from '../components/therapy/SlideManager'
import Slide1_Picture from '../components/therapy/Slide1_Picture'
import Slide2_Animation from '../components/therapy/Slide2_Animation'
import { createSessionApi } from '../features/wordSession/sessionApi'
import { createSessionFlow } from '../features/wordSession/sessionFlow'
import { useAuthStore } from '../store/authStore'

const reasonText = (reason) => {
  if (reason === 'scoring_unavailable') return 'The local word checker is not ready. Your speech will not be graded. Please ask a grown-up for help.'
  if (reason === 'assigned_plan_unavailable' || reason === 'active_word_plan_not_found') return 'There is no current therapist-assigned word plan for this session.'
  if (reason === 'word_plan_session_already_open') return 'A word session is already open. Please ask a grown-up to check it.'
  if (reason === 'word_session_break_required') return 'It is time for a break before another session.'
  return 'This word session cannot continue safely. Please ask a grown-up for help.'
}

function TeachingLesson({ lesson, onExit }) {
  const [step, setStep] = useState(1)
  return <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50">
    <div className="bg-white/70 backdrop-blur-xl shadow-sm border-b border-white/60 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
        <div className="inline-flex items-center gap-2 bg-primary/10 px-3.5 py-1.5 rounded-full">
          <span className="tamil-letter font-bold text-primary text-lg">{lesson.symbol}</span>
          <span className="text-sm font-semibold text-primary">Visual letter lesson · {step} of 2</span>
        </div>
        <button onClick={onExit} className="px-4 py-2 rounded-full text-neutral-600 hover:bg-neutral-100">Leave lesson</button>
      </div>
    </div>
    {step === 1
      ? <Slide1_Picture lesson={lesson} onNext={() => setStep(2)} silent />
      : <Slide2_Animation lesson={lesson} onPrev={() => setStep(1)} onNext={onExit} silent />}
  </div>
}

export default function TherapyPage() {
  const { lessonId } = useParams()
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [view, setView] = useState({ phase: 'loading', plans: [], snapshot: null, result: null, summary: null, reason: null })
  const flowRef = useRef(null)
  const pendingExitRef = useRef(null)
  if (!flowRef.current) flowRef.current = createSessionFlow(createSessionApi(canonicalWordClient), setView)
  const flow = flowRef.current
  const { data: lesson, isLoading: lessonLoading, isError: lessonError } = useQuery({
    queryKey: ['lesson', lessonId],
    queryFn: () => therapyAPI.getLesson(Number(lessonId)),
    enabled: Boolean(lessonId && isAuthenticated), retry: false,
  })
  const lessonData = lesson?.data
  const canScore = lessonData?.type === 'word'

  useEffect(() => {
    if (!canScore || !isAuthenticated) return undefined
    // StrictMode replays effect cleanup immediately; defer route-exit Stop until a real unmount.
    window.clearTimeout(pendingExitRef.current)
    flow.load()
    return () => {
      pendingExitRef.current = window.setTimeout(() => { flow.leave() }, 0)
    }
  }, [canScore, flow, isAuthenticated])

  if (lessonLoading) return <div className="min-h-screen bg-slide flex items-center justify-center" role="status">Loading the lesson…</div>
  if (lessonError || !lessonData) return <div className="min-h-screen bg-slide flex flex-col items-center justify-center gap-4 p-6 text-center">
    <h1 className="text-2xl font-bold">Lesson unavailable</h1><p>No word session was started.</p>
    <button onClick={() => navigate('/training')} className="px-6 py-3 bg-primary text-white rounded-full">Back to training</button>
  </div>
  if (!canScore) return <TeachingLesson key={lessonId} lesson={lessonData} onExit={() => navigate('/training')} />

  if (view.phase === 'loading') return <div className="min-h-screen bg-slide flex items-center justify-center" role="status">Checking your assigned word plan…</div>
  if (view.phase === 'select') return <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 flex items-center justify-center p-6">
    <div className="bg-white rounded-3xl shadow-2xl p-8 max-w-xl w-full">
      <h1 className="text-2xl font-bold text-neutral-900 mb-2">Choose your assigned word plan</h1>
      <p className="text-neutral-600 mb-6">These plans come from your therapist. The next word is chosen by the session.</p>
      <div className="space-y-3">{view.plans.map((plan, index) => <button key={plan.plan_id} onClick={() => flow.start(plan.plan_id)}
        className="w-full rounded-2xl border-2 border-emerald-200 bg-emerald-50 p-4 text-left hover:bg-emerald-100">
        <span className="font-bold">Assigned word plan {index + 1}</span>
        <span className="block text-sm text-neutral-600">{plan.word_ids.length} assigned {plan.word_ids.length === 1 ? 'word' : 'words'} · Start practice</span>
      </button>)}</div>
      <button onClick={() => navigate('/training')} className="mt-6 text-neutral-600 underline">Back to training</button>
    </div>
  </div>
  if (view.snapshot && ['active', 'processing', 'paused', 'ended', 'blocked'].includes(view.phase)) return <>
    {view.phase === 'blocked' && <p className="bg-amber-100 text-amber-900 text-center p-3" role="alert">{reasonText(view.reason)}</p>}
    <SlideManager snapshot={view.snapshot} phase={view.phase} reason={view.reason} result={view.result} summary={view.summary}
      onPause={() => flow.pause()} onResume={() => flow.resume()} onStop={() => flow.stop()} onSubmit={(audio) => flow.submit(audio)} />
    {view.phase === 'ended' && <button onClick={() => navigate('/dashboard')} className="block mx-auto my-6 px-6 py-3 bg-primary text-white rounded-full">Go to dashboard</button>}
  </>
  return <div className="min-h-screen bg-slide flex flex-col items-center justify-center p-6 text-center gap-4" role="alert">
    <h1 className="text-2xl font-bold">Word practice is paused</h1>
    <p className="max-w-md text-neutral-700">{reasonText(view.reason)}</p>
    <button onClick={() => navigate('/training')} className="px-6 py-3 bg-primary text-white rounded-full">Back to training</button>
  </div>
}

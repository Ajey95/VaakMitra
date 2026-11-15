import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ClipboardCheck, Type, Image as ImageIcon, Mic, Volume2, Video,
  ScanFace, Check, X, ChevronRight, RotateCcw, ArrowRight, Trophy,
  Lightbulb, Sparkles,
} from 'lucide-react'
import toast from 'react-hot-toast'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, ProgressRing, Badge, GradientButton } from '../components/ui'
import { useAuthStore } from '../store/authStore'

/* ---------------- QUIZ TYPES ---------------- */
const QUIZ_TYPES = [
  { id: 'letter', title: 'Letter Quiz', desc: 'Identify Tamil letters', icon: Type, color: 'from-primary-500 to-indigo-600', soft: 'bg-indigo-50 dark:bg-indigo-900/20' },
  { id: 'image', title: 'Image Quiz', desc: 'Match pictures to words', icon: ImageIcon, color: 'from-secondary-500 to-cyan-600', soft: 'bg-cyan-50 dark:bg-cyan-900/20' },
  { id: 'voice', title: 'Voice Quiz', desc: 'Listen and choose', icon: Mic, color: 'from-accent-500 to-emerald-600', soft: 'bg-emerald-50 dark:bg-emerald-900/20' },
  { id: 'pronunciation', title: 'Pronunciation', desc: 'Speak the word', icon: Volume2, color: 'from-gold-400 to-amber-500', soft: 'bg-amber-50 dark:bg-amber-900/20' },
  { id: 'video', title: 'Video Quiz', desc: 'Watch and answer', icon: Video, color: 'from-coral-500 to-rose-600', soft: 'bg-rose-50 dark:bg-rose-900/20' },
  { id: 'tongue', title: 'Tongue Quiz', desc: 'Movement challenge', icon: ScanFace, color: 'from-primary-500 to-secondary-500', soft: 'bg-violet-50 dark:bg-violet-900/20' },
]

/* ---------------- MOCK QUESTIONS ---------------- */
const QUESTIONS = [
  { q: 'Which letter is this?', display: 'அ', options: ['அ', 'ஆ', 'இ', 'உ'], answer: 0 },
  { q: 'Which letter makes the "ma" sound?', display: 'ம', options: ['க', 'ம', 'ந', 'ப'], answer: 1 },
  { q: 'Which letter is this?', display: 'இ', options: ['எ', 'ஐ', 'இ', 'ஈ'], answer: 2 },
  { q: 'Pick the letter "ka"', display: 'க', options: ['ச', 'த', 'ட', 'க'], answer: 3 },
  { q: 'Which letter is this?', display: 'உ', options: ['உ', 'ஊ', 'ஓ', 'ஒ'], answer: 0 },
]

const SUGGESTIONS = [
  'Review the vowels அ, ஆ, இ before retrying.',
  'Practice the "ma" and "ka" sounds with the Speech Analysis tool.',
  'Try the Letter Learning lesson for daily reinforcement.',
]

export default function AssessmentPage() {
  const { user } = useAuthStore()
  const [stage, setStage] = useState('start') // start | quiz | results
  const [quizType, setQuizType] = useState(null)
  const [current, setCurrent] = useState(0)
  const [selected, setSelected] = useState(null)
  const [answers, setAnswers] = useState([]) // { qIndex, choice, correct }

  const startQuiz = (type) => {
    setQuizType(type)
    setStage('quiz')
    setCurrent(0)
    setSelected(null)
    setAnswers([])
    toast(`${type.title} started — good luck!`, { icon: '✨' })
  }

  const choose = (i) => setSelected(i)

  const next = () => {
    if (selected === null) return toast.error('Pick an answer first')
    const correct = selected === QUESTIONS[current].answer
    const updated = [...answers, { qIndex: current, choice: selected, correct }]
    setAnswers(updated)
    if (current + 1 < QUESTIONS.length) {
      setCurrent((c) => c + 1)
      setSelected(null)
    } else {
      setStage('results')
      const score = updated.filter((a) => a.correct).length
      toast.success(`Quiz complete — ${score}/${QUESTIONS.length} correct!`)
    }
  }

  const retake = () => {
    setStage('quiz')
    setCurrent(0)
    setSelected(null)
    setAnswers([])
  }

  const backToStart = () => {
    setStage('start')
    setQuizType(null)
  }

  const correctCount = answers.filter((a) => a.correct).length
  const scorePct = Math.round((correctCount / QUESTIONS.length) * 100)
  const progress = stage === 'quiz' ? ((current) / QUESTIONS.length) * 100 : 0

  return (
    <DashboardLayout
      title="Assessment"
      subtitle={`Interactive quizzes for ${user?.child_name || user?.full_name || 'your child'}`}
      icon={ClipboardCheck}
    >
      <AnimatePresence mode="wait">
        {/* ---------- START SCREEN ---------- */}
        {stage === 'start' && (
          <motion.div
            key="start"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
          >
            <Card className="p-6 mb-6 bg-gradient-to-br from-primary-500 to-secondary-500 border-0">
              <div className="flex items-center gap-3 text-white">
                <Sparkles className="w-8 h-8" />
                <div>
                  <h2 className="text-xl font-bold">Choose an assessment</h2>
                  <p className="text-white/80 text-sm">Pick a quiz type to test your skills and earn stars.</p>
                </div>
              </div>
            </Card>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {QUIZ_TYPES.map((t, i) => {
                const Icon = t.icon
                return (
                  <motion.button
                    key={t.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.07 }}
                    whileHover={{ y: -6 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => startQuiz(t)}
                    className={`text-left p-6 rounded-3xl border border-neutral-100 dark:border-neutral-800 ${t.soft} hover:shadow-lg transition-all`}
                  >
                    <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${t.color} flex items-center justify-center mb-4 shadow-md`}>
                      <Icon className="w-7 h-7 text-white" />
                    </div>
                    <h3 className="font-bold text-neutral-900 dark:text-white text-lg mb-1">{t.title}</h3>
                    <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-3">{t.desc}</p>
                    <span className="inline-flex items-center gap-1 text-sm font-semibold text-primary-600 dark:text-primary-400">
                      Start <ChevronRight className="w-4 h-4" />
                    </span>
                  </motion.button>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* ---------- QUIZ FLOW ---------- */}
        {stage === 'quiz' && (
          <motion.div
            key="quiz"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            className="max-w-2xl mx-auto"
          >
            {/* Progress */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <Badge color="primary">{quizType?.title}</Badge>
                <span className="text-sm font-semibold text-neutral-500 dark:text-neutral-400">
                  Question {current + 1} of {QUESTIONS.length}
                </span>
              </div>
              <div className="h-2.5 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-primary-500 to-secondary-500"
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>
            </div>

            {/* Question card */}
            <AnimatePresence mode="wait">
              <motion.div
                key={current}
                initial={{ opacity: 0, x: 40 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -40 }}
              >
                <Card className="p-8">
                  <p className="text-sm font-semibold text-neutral-500 dark:text-neutral-400 mb-4 text-center">
                    {QUESTIONS[current].q}
                  </p>
                  <div className="flex justify-center mb-8">
                    <div className="w-32 h-32 rounded-3xl bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-primary-900/30 dark:to-secondary-900/30 flex items-center justify-center border border-primary-100 dark:border-primary-800/40">
                      <span className="text-7xl font-bold bg-gradient-to-br from-primary-600 to-secondary-500 bg-clip-text text-transparent">
                        {QUESTIONS[current].display}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {QUESTIONS[current].options.map((opt, i) => {
                      const isSel = selected === i
                      return (
                        <motion.button
                          key={i}
                          whileHover={{ scale: 1.03 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={() => choose(i)}
                          className={`py-5 rounded-2xl text-3xl font-bold border-2 transition-all ${
                            isSel
                              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 shadow-md'
                              : 'border-neutral-100 dark:border-neutral-800 bg-white dark:bg-neutral-900 text-neutral-700 dark:text-neutral-200 hover:border-primary-200'
                          }`}
                        >
                          {opt}
                        </motion.button>
                      )
                    })}
                  </div>

                  <div className="mt-8 flex items-center justify-between">
                    <button
                      onClick={backToStart}
                      className="text-sm font-semibold text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200 transition"
                    >
                      Exit quiz
                    </button>
                    <GradientButton onClick={next}>
                      {current + 1 === QUESTIONS.length ? 'Finish' : 'Next'}
                      <ArrowRight className="w-4 h-4" />
                    </GradientButton>
                  </div>
                </Card>
              </motion.div>
            </AnimatePresence>
          </motion.div>
        )}

        {/* ---------- RESULTS ---------- */}
        {stage === 'results' && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            className="space-y-6"
          >
            <Card className="p-8 text-center relative overflow-hidden">
              <div className="absolute -top-16 -right-16 w-56 h-56 bg-gold-400/20 rounded-full blur-3xl" />
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200, damping: 12 }}
                className="relative z-10 inline-flex w-16 h-16 rounded-2xl bg-gradient-to-br from-gold-400 to-amber-500 items-center justify-center mb-4 shadow-lg"
              >
                <Trophy className="w-8 h-8 text-white" />
              </motion.div>
              <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-1">
                {scorePct >= 80 ? 'Outstanding!' : scorePct >= 50 ? 'Good effort!' : 'Keep practicing!'}
              </h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">{quizType?.title} results</p>
              <div className="flex justify-center mb-2">
                <ProgressRing value={scorePct} size={160} stroke={12} color="#f59e0b" sublabel="score" />
              </div>
              <div className="flex items-center justify-center gap-6 mt-4">
                <div>
                  <div className="text-2xl font-bold text-accent-600 dark:text-accent-400">{correctCount}</div>
                  <div className="text-xs text-neutral-400 uppercase tracking-wide">Correct</div>
                </div>
                <div className="w-px h-8 bg-neutral-200 dark:bg-neutral-700" />
                <div>
                  <div className="text-2xl font-bold text-coral-500">{QUESTIONS.length - correctCount}</div>
                  <div className="text-xs text-neutral-400 uppercase tracking-wide">Wrong</div>
                </div>
                <div className="w-px h-8 bg-neutral-200 dark:bg-neutral-700" />
                <div>
                  <div className="text-2xl font-bold text-primary-600 dark:text-primary-400">{scorePct}%</div>
                  <div className="text-xs text-neutral-400 uppercase tracking-wide">Accuracy</div>
                </div>
              </div>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Per-question review */}
              <Card className="p-8">
                <SectionTitle title="Answer Review" subtitle="Question-by-question" icon={ClipboardCheck} />
                <div className="space-y-3">
                  {answers.map((a, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -16 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.08 }}
                      className="flex items-center gap-4 p-3 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50"
                    >
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                        a.correct ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
                          : 'bg-coral-100 dark:bg-coral-900/30 text-coral-600 dark:text-coral-400'
                      }`}>
                        {a.correct ? <Check className="w-5 h-5" /> : <X className="w-5 h-5" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 truncate">
                          {QUESTIONS[a.qIndex].q}
                        </p>
                        <p className="text-xs text-neutral-400">
                          Your answer: <span className="font-bold">{QUESTIONS[a.qIndex].options[a.choice]}</span>
                          {!a.correct && (
                            <> · Correct: <span className="font-bold text-accent-600 dark:text-accent-400">{QUESTIONS[a.qIndex].options[QUESTIONS[a.qIndex].answer]}</span></>
                          )}
                        </p>
                      </div>
                      <Badge color={a.correct ? 'accent' : 'coral'}>{a.correct ? 'Correct' : 'Wrong'}</Badge>
                    </motion.div>
                  ))}
                </div>
              </Card>

              {/* Suggestions */}
              <Card className="p-8">
                <SectionTitle title="Suggestions" subtitle="What to practice next" icon={Lightbulb} />
                <ul className="space-y-3">
                  {SUGGESTIONS.map((s, i) => (
                    <li key={i} className="flex items-start gap-3 p-4 rounded-2xl bg-gold-50 dark:bg-gold-900/20 border border-gold-100 dark:border-gold-800/40">
                      <Lightbulb className="w-5 h-5 text-gold-500 shrink-0 mt-0.5" />
                      <span className="text-sm text-neutral-700 dark:text-neutral-200">{s}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-6 flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={retake}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 font-semibold text-sm hover:bg-neutral-200 dark:hover:bg-neutral-700 transition"
                  >
                    <RotateCcw className="w-4 h-4" /> Retake
                  </button>
                  <GradientButton
                    onClick={backToStart}
                    className="flex-1"
                  >
                    Choose Another Assessment <ArrowRight className="w-4 h-4" />
                  </GradientButton>
                </div>
              </Card>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </DashboardLayout>
  )
}

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BookOpen, Volume2, RotateCcw, ChevronLeft, ChevronRight,
  Shuffle, Sparkles, Lightbulb, Star,
} from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, Badge, GradientButton } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import { repeatPhrase } from '../utils/speechRepeat'

const LETTERS = [
  { tamil: 'அ', english: 'A',  word: 'அம்மா',   wordEn: 'Amma (Mother)',   sentence: 'அம்மா எனக்கு உணவு தருகிறார்.',  tip: 'Open your mouth wide and let the sound flow from your throat — like a relaxed "ah".' },
  { tamil: 'ஆ', english: 'AA', word: 'ஆடு',     wordEn: 'Aadu (Goat)',     sentence: 'ஆடு புல் தின்கிறது.',           tip: 'Hold the open "ah" sound a little longer — stretch it gently.' },
  { tamil: 'இ', english: 'I',  word: 'இலை',     wordEn: 'Ilai (Leaf)',     sentence: 'இலை பச்சை நிறம்.',             tip: 'Smile slightly and raise the tongue near the roof — a short, bright "ih".' },
  { tamil: 'உ', english: 'U',  word: 'உப்பு',    wordEn: 'Uppu (Salt)',     sentence: 'உப்பு உணவில் சேர்க்கப்படும்.', tip: 'Round your lips into a small circle and push the sound forward — "oo".' },
  { tamil: 'எ', english: 'E',  word: 'எலி',     wordEn: 'Eli (Rat)',       sentence: 'எலி வேகமாக ஓடுகிறது.',         tip: 'Relax your jaw and spread your lips slightly for a clear "eh".' },
  { tamil: 'ல', english: 'LA', word: 'லட்டு',    wordEn: 'Laddu (Sweet)',   sentence: 'லட்டு மிகவும் இனிப்பு.',        tip: 'Touch the tip of your tongue to the ridge behind your teeth, then release.' },
  { tamil: 'த', english: 'TA', word: 'தம்பி',    wordEn: 'Thambi (Brother)',sentence: 'தம்பி பள்ளிக்கு செல்கிறான்.',  tip: 'Place the tongue softly behind the upper teeth and tap gently.' },
  { tamil: 'ம', english: 'MA', word: 'மரம்',    wordEn: 'Maram (Tree)',    sentence: 'மரம் நிழல் தருகிறது.',         tip: 'Press your lips together, hum, then open — feel the buzz on your lips.' },
  { tamil: 'ப', english: 'PA', word: 'பந்து',    wordEn: 'Panthu (Ball)',   sentence: 'பந்து உருண்டு செல்கிறது.',     tip: 'Close your lips, build a little air, then pop them open — "pa".' },
  { tamil: 'க', english: 'KA', word: 'காகம்',    wordEn: 'Kaakam (Crow)',   sentence: 'காகம் கரைகிறது.',              tip: 'Lift the back of your tongue toward the soft palate for a crisp "ka".' },
]

export default function LetterLearningPage() {
  const { user } = useAuthStore()
  const [index, setIndex] = useState(0)
  const [direction, setDirection] = useState(0)
  const current = LETTERS[index]

  const go = (next) => {
    setDirection(next > index ? 1 : -1)
    setIndex((next + LETTERS.length) % LETTERS.length)
  }
  const playSound = () => repeatPhrase(current.tamil, { lang: 'ta-IN' })
  const random = () => {
    let r = index
    while (r === index) r = Math.floor(Math.random() * LETTERS.length)
    setDirection(Math.random() > 0.5 ? 1 : -1)
    setIndex(r)
    toast.success('🎲 Surprise letter!')
  }

  return (
    <DashboardLayout
      title="Letter Learning"
      subtitle="Master the Tamil alphabet — one sound at a time"
      icon={BookOpen}
    >
      <div className="space-y-8">
        {/* HERO CARD */}
        <Card className="overflow-hidden">
          <div className="grid lg:grid-cols-2">
            {/* Big glyph */}
            <div className="relative flex items-center justify-center p-10 bg-gradient-to-br from-primary-50 via-white to-secondary-50 dark:from-primary-900/20 dark:via-neutral-900 dark:to-secondary-900/20 min-h-[320px]">
              <div className="absolute -right-8 -top-8 w-44 h-44 bg-primary-200/30 dark:bg-primary-700/20 rounded-full blur-3xl" />
              <div className="absolute -left-8 -bottom-8 w-44 h-44 bg-secondary-200/30 dark:bg-secondary-700/20 rounded-full blur-3xl" />
              <AnimatePresence mode="wait" custom={direction}>
                <motion.div
                  key={current.tamil}
                  custom={direction}
                  initial={{ opacity: 0, x: direction >= 0 ? 60 : -60, scale: 0.8 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, x: direction >= 0 ? -60 : 60, scale: 0.8 }}
                  transition={{ type: 'spring', stiffness: 260, damping: 24 }}
                  className="relative text-center"
                >
                  <div className="tamil-letter text-[12rem] leading-none font-bold bg-gradient-to-br from-primary-500 to-secondary-500 bg-clip-text text-transparent select-none">
                    {current.tamil}
                  </div>
                  <Badge color="primary" className="mt-2 text-sm px-4 py-1.5">
                    <Sparkles className="w-3.5 h-3.5" /> {current.english}
                  </Badge>
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Details */}
            <div className="p-8 flex flex-col justify-center">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">
                  Letter {index + 1} of {LETTERS.length}
                </span>
              </div>
              <AnimatePresence mode="wait">
                <motion.div
                  key={current.tamil + '-d'}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.3 }}
                >
                  <h2 className="text-3xl font-bold text-neutral-900 dark:text-white mb-4">
                    Sounds like <span className="text-primary-600 dark:text-primary-400">“{current.english}”</span>
                  </h2>
                  <div className="space-y-4">
                    <div className="rounded-2xl bg-neutral-50 dark:bg-neutral-800/60 p-4 border border-neutral-100 dark:border-neutral-800">
                      <div className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-1">Example word</div>
                      <div className="flex items-baseline gap-3">
                        <span className="tamil-letter text-2xl font-bold text-neutral-900 dark:text-white">{current.word}</span>
                        <span className="text-sm text-neutral-500 dark:text-neutral-400">{current.wordEn}</span>
                      </div>
                    </div>
                    <div className="rounded-2xl bg-neutral-50 dark:bg-neutral-800/60 p-4 border border-neutral-100 dark:border-neutral-800">
                      <div className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-1">In a sentence</div>
                      <p className="tamil-letter text-lg text-neutral-800 dark:text-neutral-100">{current.sentence}</p>
                    </div>
                  </div>
                </motion.div>
              </AnimatePresence>

              <div className="flex flex-wrap gap-3 mt-6">
                <GradientButton onClick={playSound}>
                  <Volume2 className="w-4 h-4" /> Play Sound
                </GradientButton>
                <button
                  onClick={playSound}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 font-semibold text-sm hover:bg-neutral-200 dark:hover:bg-neutral-700 transition"
                >
                  <RotateCcw className="w-4 h-4" /> Replay
                </button>
              </div>
            </div>
          </div>
        </Card>

        {/* NAVIGATION */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={() => go(index - 1)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white dark:bg-neutral-900 border border-neutral-100 dark:border-neutral-800 text-neutral-700 dark:text-neutral-200 font-semibold text-sm shadow-md hover:shadow-lg transition"
          >
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>
          <GradientButton onClick={random} className="from-gold-400 to-amber-500 shadow-amber-500/25">
            <Shuffle className="w-4 h-4" /> Random
          </GradientButton>
          <button
            onClick={() => go(index + 1)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white dark:bg-neutral-900 border border-neutral-100 dark:border-neutral-800 text-neutral-700 dark:text-neutral-200 font-semibold text-sm shadow-md hover:shadow-lg transition"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* ALPHABET STRIP */}
        <Card className="p-6">
          <SectionTitle title="Alphabet Strip" subtitle="Tap a letter to jump to it" icon={Star} />
          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
            {LETTERS.map((l, i) => {
              const active = i === index
              return (
                <motion.button
                  key={l.tamil}
                  whileHover={{ y: -4 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => go(i)}
                  className={`shrink-0 w-20 h-24 rounded-2xl flex flex-col items-center justify-center gap-1 border transition-all ${
                    active
                      ? 'bg-gradient-to-br from-primary-500 to-secondary-500 text-white border-transparent shadow-lg shadow-primary-500/30'
                      : 'bg-white dark:bg-neutral-900 text-neutral-800 dark:text-neutral-100 border-neutral-100 dark:border-neutral-800 hover:border-primary-300'
                  }`}
                >
                  <span className="tamil-letter text-3xl font-bold">{l.tamil}</span>
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${active ? 'text-white/80' : 'text-neutral-400'}`}>{l.english}</span>
                </motion.button>
              )
            })}
          </div>
        </Card>

        {/* MOUTH POSITION TIP */}
        <Card className="p-6 bg-gradient-to-br from-accent-50 to-emerald-50 dark:from-accent-900/15 dark:to-emerald-900/15 border-accent-100 dark:border-accent-800/40">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 shrink-0 bg-gradient-to-br from-accent-500 to-emerald-600 rounded-2xl flex items-center justify-center shadow-md">
              <Lightbulb className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-neutral-900 dark:text-white mb-1">Mouth Position Tip</h3>
              <AnimatePresence mode="wait">
                <motion.p
                  key={current.tamil + '-tip'}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-sm text-neutral-600 dark:text-neutral-300 leading-relaxed"
                >
                  {current.tip}
                </motion.p>
              </AnimatePresence>
            </div>
          </div>
        </Card>
      </div>
    </DashboardLayout>
  )
}

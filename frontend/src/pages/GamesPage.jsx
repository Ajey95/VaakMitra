import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Gamepad2, Star, Play, Trophy, Target, Crown, Medal, Zap,
} from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, Badge, GradientButton } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

const GAMES = [
  { name: 'Alphabet Match', emoji: '🔤', grad: 'from-primary-500 to-indigo-600',   difficulty: 1, best: 1240, path: '/games#alphabet-match' },
  { name: 'Picture Pop',    emoji: '🎈', grad: 'from-coral-500 to-rose-600',       difficulty: 2, best: 980, path: '/play/arcade/breath-balloon' },
  { name: 'Memory Flip',    emoji: '🧠', grad: 'from-secondary-500 to-cyan-600',   difficulty: 2, best: 1560, path: '/play/mouth-mirror' },
  { name: 'Sound Safari',   emoji: '🦁', grad: 'from-gold-400 to-amber-500',       difficulty: 3, best: 720, path: '/letter-learning' },
  { name: 'Pronounce Quest',emoji: '🗣️', grad: 'from-accent-500 to-emerald-600',   difficulty: 3, best: 2010, path: '/play/quest/river-rescue' },
  { name: 'Reward Rush',    emoji: '🏆', grad: 'from-violet-500 to-purple-600',    difficulty: 1, best: 1880, path: '/rewards' },
]

const LEADERBOARD = [
  { name: 'Arjun R.',  score: 2410, icon: Crown,  color: 'text-gold-500' },
  { name: 'Meena K.',  score: 2190, icon: Medal,  color: 'text-neutral-400' },
  { name: 'Vishnu P.', score: 1975, icon: Medal,  color: 'text-amber-600' },
  { name: 'Divya S.',  score: 1640, icon: Star,   color: 'text-primary-400' },
  { name: 'Karthik M.',score: 1505, icon: Star,   color: 'text-primary-400' },
]

const TAMIL = [
  { tamil: 'அ', english: 'A' },
  { tamil: 'ஆ', english: 'AA' },
  { tamil: 'இ', english: 'I' },
  { tamil: 'உ', english: 'U' },
  { tamil: 'எ', english: 'E' },
  { tamil: 'ல', english: 'LA' },
  { tamil: 'த', english: 'TA' },
  { tamil: 'ம', english: 'MA' },
  { tamil: 'ப', english: 'PA' },
  { tamil: 'க', english: 'KA' },
]

const shuffle = (arr) => [...arr].sort(() => Math.random() - 0.5)

function buildRound() {
  const pool = shuffle(TAMIL)
  const target = pool[0]
  const options = shuffle([target, ...pool.slice(1, 4)])
  return { target, options }
}

export default function GamesPage() {
  const navigate = useNavigate()
  const alphabetGameRef = useRef(null)
  const { user } = useAuthStore()
  const [round, setRound] = useState(buildRound)
  const [score, setScore] = useState(0)
  const [streak, setStreak] = useState(0)
  const [shakeId, setShakeId] = useState(null)

  const openGame = (game) => {
    if (game.path === '/games#alphabet-match') {
      navigate(game.path)
      requestAnimationFrame(() => {
        alphabetGameRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        alphabetGameRef.current?.focus({ preventScroll: true })
      })
      return
    }
    navigate(game.path)
  }

  const choose = (opt) => {
    if (opt.tamil === round.target.tamil) {
      setScore((s) => s + 10)
      setStreak((s) => s + 1)
      toast.success(`🎉 Correct! +10 points`)
      setRound(buildRound())
    } else {
      setStreak(0)
      setShakeId(opt.tamil)
      setTimeout(() => setShakeId(null), 500)
      toast.error('❌ Try again!')
    }
  }

  return (
    <DashboardLayout
      title="Mini Games"
      subtitle="Learn Tamil through play — earn points and beat your best"
      icon={Gamepad2}
    >
      <div className="space-y-8">
        {/* GAME GRID */}
        <div>
          <SectionTitle title="Game Hub" subtitle="Six ways to practice" icon={Gamepad2} />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {GAMES.map((g, i) => (
              <motion.div
                key={g.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                whileHover={{ y: -6 }}
                className={`relative rounded-3xl p-6 bg-gradient-to-br ${g.grad} text-white shadow-md overflow-hidden`}
              >
                <div className="absolute -right-6 -top-6 w-28 h-28 bg-white/15 rounded-full blur-2xl" />
                <div className="relative">
                  <div className="text-5xl mb-3">{g.emoji}</div>
                  <h3 className="text-lg font-bold mb-2">{g.name}</h3>
                  <div className="flex items-center gap-1 mb-3">
                    {[1, 2, 3].map((s) => (
                      <Star
                        key={s}
                        className={`w-4 h-4 ${s <= g.difficulty ? 'text-gold-300 fill-gold-300' : 'text-white/30'}`}
                      />
                    ))}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-white/80">
                      <span className="inline-flex items-center gap-1"><Trophy className="w-3.5 h-3.5" /> Best {g.best.toLocaleString()}</span>
                    </div>
                    <button
                      onClick={() => openGame(g)}
                      aria-label={`Play ${g.name}`}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/20 hover:bg-white/30 backdrop-blur font-semibold text-sm transition"
                    >
                      <Play className="w-4 h-4 fill-white" /> Play
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* PLAYABLE DEMO + LEADERBOARD */}
        <div
          ref={alphabetGameRef}
          id="alphabet-match"
          data-testid="alphabet-match-game"
          tabIndex={-1}
          className="grid lg:grid-cols-3 gap-6 outline-none focus-visible:ring-4 focus-visible:ring-primary-300 rounded-3xl"
        >
          {/* DEMO */}
          <Card className="lg:col-span-2 p-7">
            <div className="flex items-center justify-between mb-6">
              <SectionTitle title="Tap the Matching Letter" subtitle="Quick play demo" icon={Target} />
              <div className="flex items-center gap-3">
                <Badge color="gold"><Trophy className="w-3.5 h-3.5" /> {score}</Badge>
                <Badge color="coral"><Zap className="w-3.5 h-3.5" /> Streak {streak}</Badge>
              </div>
            </div>

            <div className="rounded-3xl bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-primary-900/20 dark:to-secondary-900/20 p-8 text-center mb-6 border border-primary-100 dark:border-primary-800/40">
              <p className="text-sm font-semibold uppercase tracking-wider text-neutral-400 mb-2">Find this letter</p>
              <AnimatePresence mode="wait">
                <motion.div
                  key={round.target.tamil}
                  initial={{ opacity: 0, scale: 0.6, rotate: -8 }}
                  animate={{ opacity: 1, scale: 1, rotate: 0 }}
                  exit={{ opacity: 0, scale: 0.6 }}
                  transition={{ type: 'spring', stiffness: 240, damping: 18 }}
                  className="tamil-letter text-7xl font-bold bg-gradient-to-br from-primary-500 to-secondary-500 bg-clip-text text-transparent"
                >
                  {round.target.english}
                </motion.div>
              </AnimatePresence>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {round.options.map((opt) => (
                <motion.button
                  key={opt.tamil}
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.95 }}
                  animate={shakeId === opt.tamil ? { x: [0, -8, 8, -8, 8, 0] } : {}}
                  transition={{ duration: 0.4 }}
                  onClick={() => choose(opt)}
                  className="aspect-square rounded-2xl bg-white dark:bg-neutral-800 border border-neutral-100 dark:border-neutral-700 flex items-center justify-center hover:border-primary-400 hover:shadow-lg transition-all"
                >
                  <span className="tamil-letter text-4xl font-bold text-neutral-800 dark:text-white">{opt.tamil}</span>
                </motion.button>
              ))}
            </div>

            <div className="mt-6 flex justify-center">
              <GradientButton onClick={() => { setRound(buildRound()); toast('🔄 New round!') }}>
                <Zap className="w-4 h-4" /> New Round
              </GradientButton>
            </div>
          </Card>

          {/* LEADERBOARD */}
          <Card className="p-6">
            <SectionTitle title="Leaderboard" subtitle="Top players" icon={Crown} />
            <div className="space-y-2.5">
              {LEADERBOARD.map((p, i) => {
                const Icon = p.icon
                return (
                  <motion.div
                    key={p.name}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06 }}
                    className="flex items-center gap-3 p-3 rounded-2xl bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-100 dark:border-neutral-800"
                  >
                    <div className="w-7 text-center font-bold text-neutral-400 text-sm">{i + 1}</div>
                    <Icon className={`w-5 h-5 ${p.color}`} />
                    <div className="flex-1 font-semibold text-neutral-800 dark:text-neutral-100 text-sm truncate">{p.name}</div>
                    <div className="font-bold text-primary-600 dark:text-primary-400 text-sm">{p.score.toLocaleString()}</div>
                  </motion.div>
                )
              })}
            </div>
            <div className="mt-4 p-3 rounded-2xl bg-gradient-to-r from-primary-500 to-secondary-500 text-white flex items-center gap-3">
              <div className="w-7 text-center font-bold text-white/80 text-sm">—</div>
              <Star className="w-5 h-5 fill-white" />
              <div className="flex-1 font-semibold text-sm truncate">
                {user?.child_name || user?.full_name || 'You'}
              </div>
              <div className="font-bold text-sm">{score.toLocaleString()}</div>
            </div>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}

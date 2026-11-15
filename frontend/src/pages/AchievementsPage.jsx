import { useState, useMemo, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Trophy, Lock, Star, Flame, Crown, Target, Sparkles, Award,
  Zap, Medal, Gem, Mic, BookOpen, Rocket, X, CheckCircle2, GraduationCap, Compass,
} from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, StatCard, SectionTitle } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { gamificationAPI } from '../services/api'

const CATEGORIES = ['All', 'Practice', 'Streaks', 'Mastery', 'Special']

const GRADS = {
  practice: 'from-primary-500 to-indigo-600',
  streaks: 'from-coral-500 to-rose-600',
  mastery: 'from-accent-500 to-emerald-600',
  special: 'from-gold-400 to-amber-500',
}
const GLOW = {
  practice: 'shadow-glow-primary',
  streaks: 'shadow-glow-coral',
  mastery: 'shadow-glow-accent',
  special: 'shadow-glow-gold',
}

// Map backend badge ids -> lucide icons (UI concern stays in the UI).
const ICON_BY_ID = {
  first_words: Mic,
  rising_star: Star,
  on_fire: Flame,
  mic_master: Mic,
  champion: Trophy,
  speech_king: Crown,
  to_the_moon: Rocket,
  legend: Gem,
  first_session: Target,
  dedicated: BookOpen,
  committed: Zap,
  explorer: Compass,
  graduate: GraduationCap,
  perfectionist: Sparkles,
  sharp_shooter: Medal,
}

export default function AchievementsPage() {
  const { user } = useAuthStore()
  const [filter, setFilter] = useState('All')
  const [selected, setSelected] = useState(null)
  const [badges, setBadges] = useState([])
  const [totalStars, setTotalStars] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    gamificationAPI
      .getAchievements('me')
      .then((res) => {
        if (!alive) return
        const data = res.data
        setBadges(
          (data.badges || []).map((b) => ({
            ...b,
            name: b.title,
            desc: b.description,
            Icon: ICON_BY_ID[b.id] || Award,
          }))
        )
        setTotalStars(data.total_stars || 0)
        setError(false)
      })
      .catch(() => alive && setError(true))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  const unlockedCount = badges.filter((b) => b.unlocked).length
  // A simple, real "level" derived from stars (every 10 stars = 1 level).
  const level = Math.floor(totalStars / 10) + 1
  const starsIntoLevel = totalStars % 10
  const levelPct = Math.round((starsIntoLevel / 10) * 100)
  const nextBadge = badges.find((b) => !b.unlocked)

  const visible = useMemo(
    () => (filter === 'All' ? badges : badges.filter((b) => b.category === filter)),
    [filter, badges]
  )

  const recent = useMemo(() => badges.filter((b) => b.unlocked).slice(0, 5), [badges])

  return (
    <DashboardLayout
      title="Achievements"
      subtitle={`Badges & milestones for ${user?.child_name || user?.full_name || 'your learner'}`}
      icon={Trophy}
    >
      {error && (
        <Card className="mb-6 p-4 border-coral-200 bg-coral-50/60">
          <p className="text-sm text-coral-700">
            Couldn&apos;t load achievements right now. Please check your connection and try again.
          </p>
        </Card>
      )}

      {/* Hero card */}
      <Card className="relative overflow-hidden p-0 mb-8">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700" />
        <div className="absolute -right-12 -top-12 w-56 h-56 bg-white/10 rounded-full blur-3xl" />
        <div className="absolute -left-10 -bottom-16 w-56 h-56 bg-gold-400/20 rounded-full blur-3xl" />
        <div className="relative z-10 p-8 grid grid-cols-1 lg:grid-cols-3 gap-8 items-center text-white">
          <div className="flex items-center gap-5">
            <motion.div
              initial={{ scale: 0, rotate: -30 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 200, damping: 14 }}
              className="w-20 h-20 bg-gradient-to-br from-gold-400 to-amber-500 rounded-3xl flex items-center justify-center shadow-glow-gold shrink-0"
            >
              <Crown className="w-10 h-10 text-white" />
            </motion.div>
            <div>
              <p className="text-white/70 text-sm font-medium">Current Level</p>
              <h2 className="text-4xl font-bold">Level {level}</h2>
              <p className="text-white/80 font-semibold">{totalStars} stars earned</p>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="font-semibold">{starsIntoLevel}/10 stars</span>
              <span className="text-white/70">to Level {level + 1}</span>
            </div>
            <div className="h-4 rounded-full bg-white/20 overflow-hidden backdrop-blur">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${levelPct}%` }}
                transition={{ duration: 1.2, ease: 'easeOut' }}
                className="h-full rounded-full bg-gradient-to-r from-gold-300 to-amber-400 shadow-glow-gold"
              />
            </div>
            <p className="text-xs text-white/70 mt-2">{levelPct}% to next level — keep going!</p>
          </div>

          <div className="flex gap-4 lg:justify-end">
            <div className="text-center bg-white/15 backdrop-blur rounded-2xl px-6 py-4">
              <div className="text-3xl font-bold">{unlockedCount}</div>
              <div className="text-xs text-white/70">Badges</div>
            </div>
            <div className="text-center bg-white/15 backdrop-blur rounded-2xl px-6 py-4">
              <div className="text-3xl font-bold">{Math.max(0, badges.length - unlockedCount)}</div>
              <div className="text-xs text-white/70">Locked</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Quick stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
        <StatCard icon={Trophy} title="Badges Unlocked" value={`${unlockedCount}/${badges.length || 0}`} sub="Keep it up!" color="gold" delay={0} />
        <StatCard icon={Star} title="Total Stars" value={totalStars} sub="From real sessions" color="primary" delay={0.05} />
        <StatCard icon={Crown} title="Level" value={level} sub={`${starsIntoLevel}/10 to next`} color="accent" delay={0.1} />
        <StatCard icon={Rocket} title="Next Milestone" value={nextBadge?.title || 'All done!'} sub={nextBadge ? nextBadge.description : 'Every badge unlocked'} color="coral" delay={0.15} />
      </div>

      {/* Category filter chips */}
      <div className="flex flex-wrap gap-2 mb-6">
        {CATEGORIES.map((cat) => {
          const active = filter === cat
          return (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-4 py-2 rounded-full text-sm font-semibold transition border ${
                active
                  ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white border-transparent shadow-md'
                  : 'bg-white dark:bg-neutral-900 text-neutral-600 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700 hover:border-primary-300'
              }`}
            >
              {cat}
            </button>
          )
        })}
      </div>

      {/* Badge grid */}
      {loading ? (
        <div className="text-center py-16 text-neutral-400">Loading achievements…</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5 mb-10">
          <AnimatePresence mode="popLayout">
            {visible.map((badge, i) => {
              const key = badge.category.toLowerCase()
              const Icon = badge.Icon
              return (
                <motion.button
                  layout
                  key={badge.id}
                  initial={{ opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.85 }}
                  transition={{ delay: i * 0.03 }}
                  whileHover={badge.unlocked ? { y: -6, scale: 1.03 } : { y: -2 }}
                  onClick={() => setSelected(badge)}
                  className={`relative rounded-3xl p-5 text-center border transition-colors ${
                    badge.unlocked
                      ? `bg-white dark:bg-neutral-900 border-neutral-100 dark:border-neutral-800 shadow-md hover:${GLOW[key]} cursor-pointer`
                      : 'bg-neutral-100 dark:bg-neutral-800/60 border-neutral-200 dark:border-neutral-700 cursor-pointer'
                  }`}
                >
                  <div
                    className={`relative w-16 h-16 mx-auto rounded-2xl flex items-center justify-center mb-3 ${
                      badge.unlocked ? `bg-gradient-to-br ${GRADS[key]} ${GLOW[key]}` : 'bg-neutral-200 dark:bg-neutral-700'
                    }`}
                  >
                    <Icon className={`w-8 h-8 ${badge.unlocked ? 'text-white' : 'text-neutral-400 dark:text-neutral-500'}`} />
                    {!badge.unlocked && (
                      <div className="absolute -bottom-1.5 -right-1.5 w-7 h-7 rounded-full bg-neutral-300 dark:bg-neutral-600 flex items-center justify-center border-2 border-white dark:border-neutral-900">
                        <Lock className="w-3.5 h-3.5 text-neutral-600 dark:text-neutral-300" />
                      </div>
                    )}
                  </div>
                  <p className={`font-bold text-sm ${badge.unlocked ? 'text-neutral-900 dark:text-white' : 'text-neutral-400 dark:text-neutral-500'}`}>
                    {badge.name}
                  </p>
                  {/* Progress toward locked badges (real) */}
                  {badge.unlocked ? (
                    <p className="text-[11px] text-accent-600 mt-1 font-semibold">Unlocked</p>
                  ) : (
                    <div className="mt-2">
                      <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-primary-400 to-secondary-400"
                          style={{ width: `${Math.round((badge.progress || 0) * 100)}%` }}
                        />
                      </div>
                      <p className="text-[11px] text-neutral-400 mt-1">
                        {badge.current}/{badge.threshold}
                      </p>
                    </div>
                  )}
                </motion.button>
              )
            })}
          </AnimatePresence>
        </div>
      )}

      {/* Recently unlocked */}
      {recent.length > 0 && (
        <Card className="p-6">
          <SectionTitle title="Unlocked Badges" subtitle="Milestones you've already earned" icon={CheckCircle2} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {recent.map((item, i) => {
              const Icon = item.Icon
              const dot = GRADS[item.category.toLowerCase()]
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -16 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08 }}
                  className="flex items-center gap-4 bg-neutral-50 dark:bg-neutral-800/50 rounded-2xl px-4 py-3 border border-neutral-100 dark:border-neutral-800"
                >
                  <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${dot} flex items-center justify-center shadow-md shrink-0`}>
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="font-bold text-neutral-900 dark:text-white text-sm">{item.title}</p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">{item.description}</p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Badge detail modal */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelected(null)}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/60 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.85, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.85, opacity: 0, y: 20 }}
              transition={{ type: 'spring', stiffness: 300, damping: 24 }}
              onClick={(e) => e.stopPropagation()}
              className="relative bg-white dark:bg-neutral-900 rounded-3xl shadow-premium-lg border border-neutral-100 dark:border-neutral-800 max-w-sm w-full p-8 text-center"
            >
              <button
                onClick={() => setSelected(null)}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
              {(() => {
                const key = selected.category.toLowerCase()
                const Icon = selected.Icon
                return (
                  <motion.div
                    initial={{ scale: 0, rotate: -20 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: 'spring', stiffness: 200, damping: 12, delay: 0.1 }}
                    className={`w-24 h-24 mx-auto rounded-3xl flex items-center justify-center mb-5 bg-gradient-to-br ${
                      selected.unlocked ? `${GRADS[key]} ${GLOW[key]}` : 'from-neutral-300 to-neutral-400'
                    }`}
                  >
                    <Icon className="w-12 h-12 text-white" />
                  </motion.div>
                )
              })()}
              {selected.unlocked ? (
                <span className="inline-flex items-center gap-1.5 text-accent-600 text-sm font-semibold mb-3">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Unlocked
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-neutral-400 text-sm font-semibold mb-3">
                  <Lock className="w-3.5 h-3.5" /> Locked
                </span>
              )}
              <h3 className="text-2xl font-bold text-neutral-900 dark:text-white">{selected.title}</h3>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2 mb-5">{selected.description}</p>
              <div className="flex items-center justify-center gap-6 text-sm">
                <div>
                  <p className="text-neutral-400 text-xs">Progress</p>
                  <p className="font-bold text-neutral-800 dark:text-neutral-100">{selected.current}/{selected.threshold}</p>
                </div>
                <div className="w-px h-8 bg-neutral-200 dark:bg-neutral-700" />
                <div>
                  <p className="text-neutral-400 text-xs">Category</p>
                  <p className="font-bold text-neutral-800 dark:text-neutral-100">{selected.category}</p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </DashboardLayout>
  )
}

import { useState, useEffect, useRef } from 'react'
import { motion, useMotionValue, animate, AnimatePresence } from 'framer-motion'
import {
  Gift, Coins, Star, Gem, Flame, Crown, ShoppingBag, Check,
  Palette, Sticker, Smile, Sparkles, Music, Shirt, Trophy,
} from 'lucide-react'
import toast from 'react-hot-toast'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, StatCard, SectionTitle, ProgressRing, Badge } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { gamificationAPI } from '../services/api'

/* ------------------------------------------------------------------ */
/*  MOCK DATA                                                          */
/* ------------------------------------------------------------------ */

const WALLET_START = { coins: 1240, stars: 318, gems: 26 }
const LEVEL = { current: 7, title: 'Sound Explorer', progress: 76 }

const SHOP = [
  { id: 1, name: 'Star Sticker Pack', type: 'Sticker', icon: Sticker, cost: 120, color: 'gold' },
  { id: 2, name: 'Ocean Theme', type: 'Theme', icon: Palette, cost: 300, color: 'secondary' },
  { id: 3, name: 'Robot Avatar', type: 'Avatar', icon: Smile, cost: 450, color: 'primary' },
  { id: 4, name: 'Sparkle Effects', type: 'Effect', icon: Sparkles, cost: 200, color: 'gold' },
  { id: 5, name: 'Victory Jingle', type: 'Sound', icon: Music, cost: 180, color: 'accent' },
  { id: 6, name: 'Superhero Cape', type: 'Outfit', icon: Shirt, cost: 600, color: 'coral' },
  { id: 7, name: 'Galaxy Theme', type: 'Theme', icon: Palette, cost: 500, color: 'primary' },
  { id: 8, name: 'Animal Stickers', type: 'Sticker', icon: Sticker, cost: 90, color: 'accent' },
]

const STREAK = [
  { day: 'Mon', done: true }, { day: 'Tue', done: true }, { day: 'Wed', done: true },
  { day: 'Thu', done: true }, { day: 'Fri', done: true }, { day: 'Sat', done: false },
  { day: 'Sun', done: false },
]

const LEADERBOARD = [
  { rank: 1, name: 'Arjun K.', xp: 5820, me: false },
  { rank: 2, name: 'Meena R.', xp: 5410, me: false },
  { rank: 3, name: 'Karthik V.', xp: 4990, me: false },
  { rank: 4, name: 'You', xp: 4760, me: true },
  { rank: 5, name: 'Divya S.', xp: 4520, me: false },
  { rank: 6, name: 'Ravi T.', xp: 4180, me: false },
  { rank: 7, name: 'Anya P.', xp: 3940, me: false },
  { rank: 8, name: 'Surya M.', xp: 3710, me: false },
  { rank: 9, name: 'Nila J.', xp: 3500, me: false },
  { rank: 10, name: 'Vikram D.', xp: 3290, me: false },
]

/* Animated number counter */
function Counter({ value }) {
  const mv = useMotionValue(0)
  const ref = useRef(null)
  useEffect(() => {
    const controls = animate(mv, value, {
      duration: 1.4,
      ease: 'easeOut',
      onUpdate: (v) => {
        if (ref.current) ref.current.textContent = Math.round(v).toLocaleString()
      },
    })
    return controls.stop
  }, [value, mv])
  return <span ref={ref}>0</span>
}

const RANK_STYLES = {
  1: { ring: 'from-gold-400 to-amber-500', label: '🥇' },
  2: { ring: 'from-neutral-300 to-neutral-400', label: '🥈' },
  3: { ring: 'from-amber-600 to-amber-700', label: '🥉' },
}

const SOFT = {
  primary: 'bg-indigo-50 dark:bg-neutral-800/60 border-indigo-100 dark:border-neutral-700',
  secondary: 'bg-cyan-50 dark:bg-neutral-800/60 border-cyan-100 dark:border-neutral-700',
  accent: 'bg-emerald-50 dark:bg-neutral-800/60 border-emerald-100 dark:border-neutral-700',
  gold: 'bg-amber-50 dark:bg-neutral-800/60 border-amber-100 dark:border-neutral-700',
  coral: 'bg-rose-50 dark:bg-neutral-800/60 border-rose-100 dark:border-neutral-700',
}
const GRAD = {
  primary: 'from-primary-500 to-indigo-600',
  secondary: 'from-secondary-500 to-cyan-600',
  accent: 'from-accent-500 to-emerald-600',
  gold: 'from-gold-400 to-amber-500',
  coral: 'from-coral-500 to-rose-600',
}

export default function RewardsPage() {
  const { user } = useAuthStore()
  const [coins, setCoins] = useState(WALLET_START.coins)
  const [owned, setOwned] = useState([])
  const [leaderboard, setLeaderboard] = useState([])
  const [realStars, setRealStars] = useState(null)

  useEffect(() => {
    let alive = true
    gamificationAPI
      .getLeaderboard(10)
      .then((res) => {
        if (alive) setLeaderboard(res.data.leaderboard || [])
      })
      .catch(() => {})
    gamificationAPI
      .getAchievements('me')
      .then((res) => {
        if (alive) setRealStars(res.data.total_stars ?? null)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  // Real stars earned drive both the wallet and the leaderboard rows.
  const starsValue = realStars ?? WALLET_START.stars
  const board = leaderboard.length > 0 ? leaderboard : null

  const redeem = (item) => {
    if (owned.includes(item.id)) return
    if (coins < item.cost) {
      toast.error(`Need ${item.cost - coins} more coins for ${item.name}`)
      return
    }
    setCoins((c) => c - item.cost)
    setOwned((o) => [...o, item.id])
    toast.success(`🎁 Redeemed ${item.name}!`)
  }

  return (
    <DashboardLayout
      title="Rewards & Gamification"
      subtitle={`Spend coins, climb the leaderboard, and keep your streak alive, ${user?.child_name || 'champ'}!`}
      icon={Gift}
    >
      {/* Wallet */}
      <Card className="relative overflow-hidden p-0 mb-8">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-600 via-secondary-600 to-secondary-700" />
        <div className="absolute -right-10 -top-12 w-52 h-52 bg-gold-300/20 rounded-full blur-3xl" />
        <div className="absolute -left-8 bottom-0 w-44 h-44 bg-white/10 rounded-full blur-3xl" />
        <div className="relative z-10 p-8 text-white">
          <div className="flex items-center gap-2 mb-6">
            <ShoppingBag className="w-5 h-5" />
            <h2 className="text-lg font-bold">My Wallet</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {[
              { icon: Coins, label: 'Coins', value: coins, tint: 'from-gold-300 to-amber-400' },
              { icon: Star, label: 'Stars', value: starsValue, tint: 'from-yellow-200 to-gold-300' },
              { icon: Gem, label: 'Gems', value: WALLET_START.gems, tint: 'from-cyan-200 to-secondary-300' },
            ].map((w, i) => (
              <motion.div
                key={w.label}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="bg-white/15 backdrop-blur rounded-2xl p-5 flex items-center gap-4"
              >
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${w.tint} flex items-center justify-center shadow-md`}>
                  <w.icon className="w-7 h-7 text-white" />
                </div>
                <div>
                  <div className="text-3xl font-bold tabular-nums">
                    <Counter value={w.value} />
                  </div>
                  <div className="text-xs text-white/70 uppercase tracking-wide">{w.label}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* Level progress */}
        <Card className="p-6 flex flex-col items-center justify-center text-center">
          <SectionTitle title="Level Progress" icon={Crown} />
          <ProgressRing value={LEVEL.progress} size={160} stroke={14} color="#F59E0B" label={`Lv ${LEVEL.current}`} sublabel={LEVEL.title} />
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-4">
            <span className="font-bold text-gold-600">{100 - LEVEL.progress}%</span> to Level {LEVEL.current + 1}
          </p>
        </Card>

        {/* Streak calendar */}
        <Card className="p-6 lg:col-span-2">
          <SectionTitle
            title="Weekly Streak"
            subtitle="5-day streak — keep the flame burning!"
            icon={Flame}
            action={<Badge color="coral"><Flame className="w-3.5 h-3.5" /> 5 days</Badge>}
          />
          <div className="grid grid-cols-7 gap-2 sm:gap-3">
            {STREAK.map((d, i) => (
              <motion.div
                key={d.day}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.06 }}
                className={`rounded-2xl py-4 flex flex-col items-center gap-2 border ${
                  d.done
                    ? 'bg-gradient-to-br from-coral-500 to-rose-600 border-transparent shadow-glow-coral'
                    : 'bg-neutral-50 dark:bg-neutral-800/60 border-neutral-200 dark:border-neutral-700'
                }`}
              >
                <span className={`text-[11px] font-bold ${d.done ? 'text-white/80' : 'text-neutral-400'}`}>{d.day}</span>
                <Flame className={`w-6 h-6 ${d.done ? 'text-white' : 'text-neutral-300 dark:text-neutral-600'}`} />
              </motion.div>
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
            <StatCard icon={Flame} title="Current Streak" value="5 days" sub="On fire!" color="coral" />
            <StatCard icon={Trophy} title="Longest Streak" value="14 days" sub="Personal best" color="gold" />
          </div>
        </Card>
      </div>

      {/* Rewards shop */}
      <Card className="p-6 mb-8">
        <SectionTitle
          title="Rewards Shop"
          subtitle="Redeem your coins for fun items"
          icon={ShoppingBag}
          action={<Badge color="gold"><Coins className="w-3.5 h-3.5" /> {coins.toLocaleString()} coins</Badge>}
        />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
          {SHOP.map((item, i) => {
            const isOwned = owned.includes(item.id)
            const affordable = coins >= item.cost
            const Icon = item.icon
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                whileHover={{ y: -5 }}
                className={`rounded-3xl p-5 border text-center ${SOFT[item.color]}`}
              >
                <div className={`w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br ${GRAD[item.color]} flex items-center justify-center shadow-md mb-3`}>
                  <Icon className="w-8 h-8 text-white" />
                </div>
                <p className="font-bold text-sm text-neutral-900 dark:text-white">{item.name}</p>
                <p className="text-[11px] text-neutral-400 mb-3">{item.type}</p>
                <div className="flex items-center justify-center gap-1 mb-3 text-gold-600 font-bold">
                  <Coins className="w-4 h-4" /> {item.cost}
                </div>
                <button
                  onClick={() => redeem(item)}
                  disabled={isOwned || !affordable}
                  className={`w-full inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold transition ${
                    isOwned
                      ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-700 dark:text-accent-300 cursor-default'
                      : affordable
                      ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-md hover:shadow-lg'
                      : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-400 dark:text-neutral-500 cursor-not-allowed'
                  }`}
                >
                  {isOwned ? (<><Check className="w-4 h-4" /> Owned</>) : 'Redeem'}
                </button>
              </motion.div>
            )
          })}
        </div>
      </Card>

      {/* Leaderboard */}
      <Card className="p-6">
        <SectionTitle title="Leaderboard" subtitle="Top learners by stars earned" icon={Trophy} action={board ? <Badge color="accent">Live</Badge> : <Badge color="neutral">Sample</Badge>} />
        <div className="space-y-2">
          {(board || LEADERBOARD).map((p, i) => {
            // Normalize both shapes: backend {rank,name,stars,is_me} or mock {rank,name,xp,me}
            const isMe = p.is_me ?? p.me
            const score = p.stars ?? p.xp
            const scoreLabel = board ? `${(score || 0).toLocaleString()}` : `${(score || 0).toLocaleString()} XP`
            const medal = RANK_STYLES[p.rank]
            return (
              <motion.div
                key={p.rank}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                className={`flex items-center gap-4 px-4 py-3 rounded-2xl border transition ${
                  isMe
                    ? 'bg-gradient-to-r from-primary-50 to-secondary-50 dark:from-primary-900/30 dark:to-secondary-900/30 border-primary-200 dark:border-primary-700 shadow-md'
                    : 'bg-white dark:bg-neutral-900 border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50'
                }`}
              >
                <div className="w-9 text-center font-bold text-neutral-500 dark:text-neutral-400">
                  {medal ? <span className="text-xl">{medal.label}</span> : `#${p.rank}`}
                </div>
                <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${medal ? medal.ring : 'from-primary-500 to-secondary-500'} flex items-center justify-center text-white font-bold shadow-md shrink-0`}>
                  {(p.name || '?').charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`font-bold text-sm truncate ${isMe ? 'text-primary-700 dark:text-primary-300' : 'text-neutral-900 dark:text-white'}`}>
                    {p.name} {isMe && <Badge color="primary" className="ml-1">You</Badge>}
                  </p>
                  <p className="text-xs text-neutral-400">Rank #{p.rank}</p>
                </div>
                <div className="flex items-center gap-1.5 font-bold text-gold-600 shrink-0">
                  <Sparkles className="w-4 h-4" /> {scoreLabel}
                </div>
              </motion.div>
            )
          })}
        </div>
      </Card>
    </DashboardLayout>
  )
}

import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell, Trophy, CalendarClock, AlarmClock, MessageSquare, Sparkles,
  CheckCheck, X, BellOff, Mail, Smartphone, Volume2,
} from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, EmptyState } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

const TYPE_META = {
  achievement: { icon: Trophy, grad: 'from-gold-400 to-amber-500', soft: 'bg-amber-50 dark:bg-amber-900/20' },
  appointment: { icon: CalendarClock, grad: 'from-primary-500 to-indigo-600', soft: 'bg-indigo-50 dark:bg-indigo-900/20' },
  reminder: { icon: AlarmClock, grad: 'from-secondary-500 to-cyan-600', soft: 'bg-cyan-50 dark:bg-cyan-900/20' },
  message: { icon: MessageSquare, grad: 'from-accent-500 to-emerald-600', soft: 'bg-emerald-50 dark:bg-emerald-900/20' },
}

const INITIAL_NOTIFS = [
  { id: 1, type: 'achievement', title: 'New Badge Unlocked!', message: 'Aarav earned the "Vowel Master" badge for completing 20 vowel drills.', time: '15 min ago', group: 'today', unread: true },
  { id: 2, type: 'appointment', title: 'Session in 1 hour', message: 'Video call with Dr. Anitha Raman at 4:30 PM. Tap to join early.', time: '40 min ago', group: 'today', unread: true },
  { id: 3, type: 'reminder', title: 'Daily Practice Reminder', message: 'You have 2 pending exercises. A quick 10-minute session keeps the streak alive!', time: '2 hours ago', group: 'today', unread: true },
  { id: 4, type: 'message', title: 'Note from Therapist', message: 'Dr. Karthik shared feedback on the tongue placement assessment.', time: '3 hours ago', group: 'today', unread: false },
  { id: 5, type: 'achievement', title: '7-Day Streak!', message: 'Amazing consistency — you have practised every day this week.', time: '5 hours ago', group: 'today', unread: false },
  { id: 6, type: 'appointment', title: 'Appointment Confirmed', message: 'Your session on the 18th with Dr. Karthik S. is confirmed.', time: 'Yesterday', group: 'earlier', unread: false },
  { id: 7, type: 'reminder', title: 'Progress Report Ready', message: 'Your weekly progress report is now available to view and download.', time: 'Yesterday', group: 'earlier', unread: true },
  { id: 8, type: 'message', title: 'Parent Hub Reply', message: 'A specialist replied to your question in the Parent Community.', time: '2 days ago', group: 'earlier', unread: false },
  { id: 9, type: 'achievement', title: 'Level Up!', message: 'Aarav advanced to Level 4 — Sentence Building. New lessons unlocked.', time: '2 days ago', group: 'earlier', unread: false },
  { id: 10, type: 'reminder', title: 'Holiday Mode Ending', message: 'Holiday Mode ends tomorrow. Sessions will resume automatically.', time: '3 days ago', group: 'earlier', unread: false },
  { id: 11, type: 'appointment', title: 'Reschedule Suggested', message: 'Dr. Priya Mohan proposed a new time for your candle-test session.', time: '4 days ago', group: 'earlier', unread: false },
  { id: 12, type: 'message', title: 'Welcome to SpeakEasy ASD', message: 'Thanks for joining! Explore the dashboard to begin your therapy journey.', time: '1 week ago', group: 'earlier', unread: false },
]

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'unread', label: 'Unread' },
  { key: 'achievement', label: 'Achievements' },
  { key: 'appointment', label: 'Appointments' },
  { key: 'reminder', label: 'Reminders' },
]

function Toggle({ on, onChange }) {
  return (
    <button
      onClick={onChange}
      className={`relative w-11 h-6 rounded-full transition-colors ${on ? 'bg-primary-500' : 'bg-neutral-300 dark:bg-neutral-700'}`}
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow ${on ? 'left-[22px]' : 'left-0.5'}`}
      />
    </button>
  )
}

function NotifRow({ n, onRead, onDelete, index }) {
  const meta = TYPE_META[n.type]
  const Icon = meta.icon
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -40, transition: { duration: 0.2 } }}
      transition={{ delay: index * 0.03 }}
      onClick={() => n.unread && onRead(n.id)}
      className={`group relative flex items-start gap-4 p-4 rounded-2xl border transition cursor-pointer ${
        n.unread
          ? 'bg-white dark:bg-neutral-900 border-primary-100 dark:border-primary-900/40 shadow-sm'
          : 'bg-neutral-50/60 dark:bg-neutral-800/30 border-neutral-100 dark:border-neutral-800'
      } hover:shadow-md`}
    >
      <div className={`w-11 h-11 shrink-0 rounded-xl bg-gradient-to-br ${meta.grad} flex items-center justify-center shadow-md`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h4 className={`text-sm truncate ${n.unread ? 'font-bold text-neutral-900 dark:text-white' : 'font-semibold text-neutral-600 dark:text-neutral-300'}`}>
            {n.title}
          </h4>
          {n.unread && <span className="w-2 h-2 rounded-full bg-coral-500 shrink-0" />}
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1 leading-relaxed">{n.message}</p>
        <span className="text-[11px] text-neutral-400 mt-1.5 inline-block">{n.time}</span>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(n.id) }}
        className="opacity-0 group-hover:opacity-100 transition p-1.5 rounded-lg text-neutral-400 hover:bg-coral-50 hover:text-coral-500 dark:hover:bg-coral-900/30 shrink-0"
        title="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  )
}

export default function NotificationsPage() {
  const { user } = useAuthStore()
  const [notifs, setNotifs] = useState(INITIAL_NOTIFS)
  const [filter, setFilter] = useState('all')
  const [prefs, setPrefs] = useState({ email: true, push: true, sound: false })

  const markRead = (id) => setNotifs((list) => list.map((n) => (n.id === id ? { ...n, unread: false } : n)))
  const deleteNotif = (id) => {
    setNotifs((list) => list.filter((n) => n.id !== id))
    toast.success('Notification dismissed')
  }
  const markAllRead = () => {
    setNotifs((list) => list.map((n) => ({ ...n, unread: false })))
    toast.success('All marked as read')
  }
  const togglePref = (key) => setPrefs((p) => ({ ...p, [key]: !p[key] }))

  const filtered = useMemo(() => {
    if (filter === 'all') return notifs
    if (filter === 'unread') return notifs.filter((n) => n.unread)
    return notifs.filter((n) => n.type === filter)
  }, [notifs, filter])

  const today = filtered.filter((n) => n.group === 'today')
  const earlier = filtered.filter((n) => n.group === 'earlier')
  const unreadCount = notifs.filter((n) => n.unread).length

  const renderGroup = (label, items, offset) =>
    items.length > 0 && (
      <div>
        <div className="text-[11px] font-bold uppercase tracking-wider text-neutral-400 mb-3 px-1">{label}</div>
        <div className="space-y-2.5">
          <AnimatePresence>
            {items.map((n, i) => (
              <NotifRow key={n.id} n={n} index={i + offset} onRead={markRead} onDelete={deleteNotif} />
            ))}
          </AnimatePresence>
        </div>
      </div>
    )

  return (
    <DashboardLayout
      title="Notifications"
      subtitle={`${unreadCount} unread update${unreadCount === 1 ? '' : 's'}`}
      icon={Bell}
      actions={
        <button
          onClick={markAllRead}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm bg-white/15 text-white border border-white/20 hover:bg-white/25 transition"
        >
          <CheckCheck className="w-4 h-4" /> Mark all read
        </button>
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Filter tabs */}
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => {
              const active = filter === f.key
              return (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition ${
                    active
                      ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-md shadow-primary-500/25'
                      : 'bg-white dark:bg-neutral-900 text-neutral-600 dark:text-neutral-300 border border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800'
                  }`}
                >
                  {f.label}
                  {f.key === 'unread' && unreadCount > 0 && (
                    <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] ${active ? 'bg-white/25' : 'bg-coral-100 text-coral-600 dark:bg-coral-900/40 dark:text-coral-300'}`}>
                      {unreadCount}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* List */}
          {filtered.length === 0 ? (
            <Card className="p-4">
              <EmptyState
                icon={BellOff}
                title="You're all caught up"
                description="There are no notifications in this filter. Check back later for new updates."
              />
            </Card>
          ) : (
            <div className="space-y-7">
              {renderGroup('Today', today, 0)}
              {renderGroup('Earlier', earlier, today.length)}
            </div>
          )}
        </div>

        {/* Preferences mini-card */}
        <div className="space-y-6">
          <Card className="p-6" delay={0.1}>
            <SectionTitle title="Preferences" subtitle="Choose how you hear from us" icon={Sparkles} />
            <div className="space-y-4">
              {[
                { key: 'email', label: 'Email Alerts', desc: 'Session & report summaries', icon: Mail },
                { key: 'push', label: 'Push Notifications', desc: 'Real-time reminders on device', icon: Smartphone },
                { key: 'sound', label: 'Sound Effects', desc: 'Play a chime for new alerts', icon: Volume2 },
              ].map((p) => {
                const Icon = p.icon
                return (
                  <div key={p.key} className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center shrink-0">
                      <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{p.label}</div>
                      <div className="text-xs text-neutral-400">{p.desc}</div>
                    </div>
                    <Toggle on={prefs[p.key]} onChange={() => togglePref(p.key)} />
                  </div>
                )
              })}
            </div>
          </Card>

          <Card className="p-6 bg-gradient-to-br from-primary-500 to-secondary-500 !border-0" delay={0.2}>
            <Trophy className="w-8 h-8 text-white/90 mb-3" />
            <h3 className="text-white font-bold text-lg">Stay motivated</h3>
            <p className="text-white/80 text-sm mt-1">
              Enable reminders to keep {user?.child_name || 'your child'}'s daily streak going strong.
            </p>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}

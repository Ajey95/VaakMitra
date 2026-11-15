import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Calendar as CalendarIcon, ChevronLeft, ChevronRight, CalendarClock,
  CheckCircle2, XCircle, Flame, Palmtree, Clock, MapPin, Video, Dot,
} from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, StatCard, SectionTitle, Badge, EmptyState, GradientButton } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

// Mock sessions are spread across the *current* month by day-of-month so the
// calendar always looks populated regardless of when it is viewed.
const MOCK_SESSIONS = [
  { day: 2, time: '10:00 AM', title: 'Vowel Sounds — அ ஆ இ', therapist: 'Dr. Anitha Raman', mode: 'video', status: 'completed' },
  { day: 4, time: '04:30 PM', title: 'Tongue Placement Drill', therapist: 'Dr. Karthik S.', mode: 'in-person', status: 'completed' },
  { day: 6, time: '11:00 AM', title: 'Picture Naming — Animals', therapist: 'Dr. Anitha Raman', mode: 'video', status: 'completed' },
  { day: 9, time: '03:00 PM', title: 'Breathing & Candle Test', therapist: 'Dr. Priya Mohan', mode: 'video', status: 'missed' },
  { day: 11, time: '10:30 AM', title: 'Consonant Blends — க ங', therapist: 'Dr. Karthik S.', mode: 'in-person', status: 'completed' },
  { day: 14, time: '05:00 PM', title: 'Sentence Building Practice', therapist: 'Dr. Anitha Raman', mode: 'video', status: 'completed' },
  { day: 16, time: '09:30 AM', title: 'Rhythm & Syllable Clapping', therapist: 'Dr. Priya Mohan', mode: 'video', status: 'upcoming' },
  { day: 18, time: '02:00 PM', title: 'Story Retell — தமிழ்', therapist: 'Dr. Karthik S.', mode: 'in-person', status: 'upcoming' },
  { day: 21, time: '11:30 AM', title: 'Pronunciation Assessment', therapist: 'Dr. Anitha Raman', mode: 'video', status: 'upcoming' },
  { day: 23, time: '04:00 PM', title: 'Interactive Speech Game', therapist: 'Dr. Priya Mohan', mode: 'video', status: 'upcoming' },
  { day: 26, time: '10:00 AM', title: 'Parent Coaching Session', therapist: 'Dr. Karthik S.', mode: 'in-person', status: 'upcoming' },
  { day: 28, time: '03:30 PM', title: 'Monthly Progress Review', therapist: 'Dr. Anitha Raman', mode: 'video', status: 'upcoming' },
]

const STATUS_DOT = {
  completed: 'bg-accent-500',
  upcoming: 'bg-primary-500',
  missed: 'bg-coral-500',
}
const STATUS_BADGE = { completed: 'accent', upcoming: 'primary', missed: 'coral' }

export default function CalendarPage() {
  const { user } = useAuthStore()
  const today = new Date()
  const [viewDate, setViewDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1))
  const [selectedDay, setSelectedDay] = useState(today.getDate())
  const [holidayMode, setHolidayMode] = useState(false)
  const [reminders, setReminders] = useState(() => new Set())

  const year = viewDate.getFullYear()
  const month = viewDate.getMonth()
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month

  const grid = useMemo(() => {
    const firstWeekday = new Date(year, month, 1).getDay()
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const cells = []
    for (let i = 0; i < firstWeekday; i++) cells.push(null)
    for (let d = 1; d <= daysInMonth; d++) cells.push(d)
    while (cells.length % 7 !== 0) cells.push(null)
    return cells
  }, [year, month])

  const sessionsByDay = useMemo(() => {
    const map = {}
    MOCK_SESSIONS.forEach((s) => {
      if (!map[s.day]) map[s.day] = []
      map[s.day].push(s)
    })
    return map
  }, [])

  const stats = useMemo(() => {
    const upcoming = MOCK_SESSIONS.filter((s) => s.status === 'upcoming').length
    const completed = MOCK_SESSIONS.filter((s) => s.status === 'completed').length
    const missed = MOCK_SESSIONS.filter((s) => s.status === 'missed').length
    return { upcoming, completed, missed, streak: 7 }
  }, [])

  const selectedSessions = sessionsByDay[selectedDay] || []

  const changeMonth = (delta) => {
    const next = new Date(year, month + delta, 1)
    setViewDate(next)
    setSelectedDay(1)
  }

  const toggleHoliday = () => {
    setHolidayMode((v) => {
      const nv = !v
      toast.success(nv ? 'Holiday Mode on — sessions paused' : 'Holiday Mode off — schedule resumed')
      return nv
    })
  }

  const toggleReminder = (session) => {
    const key = `${year}-${month}-${selectedDay}-${session.title}`
    setReminders((previous) => {
      const next = new Set(previous)
      if (next.has(key)) {
        next.delete(key)
        toast.success('Reminder removed')
      } else {
        next.add(key)
        toast.success('Reminder saved on this device')
      }
      return next
    })
  }

  return (
    <DashboardLayout
      title="Therapy Calendar"
      subtitle="Plan, track and review every speech session"
      icon={CalendarIcon}
      actions={
        <button
          onClick={toggleHoliday}
          className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm transition border ${
            holidayMode
              ? 'bg-gold-400 text-white border-gold-400 shadow-md'
              : 'bg-white/15 text-white border-white/20 hover:bg-white/25'
          }`}
        >
          <Palmtree className="w-4 h-4" />
          Holiday Mode {holidayMode ? 'On' : 'Off'}
        </button>
      }
    >
      <div className="space-y-8">
        {/* Summary stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <StatCard icon={CalendarClock} title="Upcoming" value={stats.upcoming} color="primary" delay={0} />
          <StatCard icon={CheckCircle2} title="Completed" value={stats.completed} color="accent" sub="This month" delay={0.05} />
          <StatCard icon={XCircle} title="Missed" value={stats.missed} color="coral" delay={0.1} />
          <StatCard icon={Flame} title="Day Streak" value={stats.streak} color="gold" sub="Keep it going!" delay={0.15} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar grid */}
          <Card className="lg:col-span-2 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-neutral-900 dark:text-white">
                {MONTHS[month]} {year}
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => changeMonth(-1)}
                  className="p-2 rounded-xl text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={() => { setViewDate(new Date(today.getFullYear(), today.getMonth(), 1)); setSelectedDay(today.getDate()) }}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 hover:bg-primary-100 transition"
                >
                  Today
                </button>
                <button
                  onClick={() => changeMonth(1)}
                  className="p-2 rounded-xl text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-7 gap-1 mb-2">
              {WEEKDAYS.map((w) => (
                <div key={w} className="text-center text-[11px] font-bold uppercase tracking-wider text-neutral-400 py-2">
                  {w}
                </div>
              ))}
            </div>

            <div className={`grid grid-cols-7 gap-1.5 ${holidayMode ? 'opacity-50 pointer-events-none' : ''}`}>
              {grid.map((day, idx) => {
                if (day === null) return <div key={`e-${idx}`} className="aspect-square" />
                const daySessions = sessionsByDay[day] || []
                const isToday = isCurrentMonth && day === today.getDate()
                const isSelected = day === selectedDay
                return (
                  <motion.button
                    key={day}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setSelectedDay(day)}
                    className={`aspect-square rounded-2xl flex flex-col items-center justify-center gap-1 text-sm font-semibold transition-all relative ${
                      isSelected
                        ? 'bg-gradient-to-br from-primary-500 to-secondary-500 text-white shadow-lg shadow-primary-500/30'
                        : isToday
                        ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 ring-2 ring-primary-300'
                        : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                    }`}
                  >
                    <span>{day}</span>
                    {daySessions.length > 0 && (
                      <span className="flex items-center gap-0.5 absolute bottom-1.5">
                        {daySessions.slice(0, 3).map((s, i) => (
                          <span
                            key={i}
                            className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-white' : STATUS_DOT[s.status]}`}
                          />
                        ))}
                      </span>
                    )}
                  </motion.button>
                )
              })}
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center gap-4 mt-6 pt-5 border-t border-neutral-100 dark:border-neutral-800">
              {[
                { label: 'Completed', cls: 'bg-accent-500' },
                { label: 'Upcoming', cls: 'bg-primary-500' },
                { label: 'Missed', cls: 'bg-coral-500' },
              ].map((l) => (
                <div key={l.label} className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${l.cls}`} />
                  <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">{l.label}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Side panel */}
          <Card className="p-6" delay={0.1}>
            <SectionTitle
              title={`${MONTHS[month]} ${selectedDay}`}
              subtitle={`${selectedSessions.length} session${selectedSessions.length === 1 ? '' : 's'} scheduled`}
              icon={CalendarClock}
            />

            {holidayMode ? (
              <EmptyState
                icon={Palmtree}
                title="Holiday Mode is on"
                description="Sessions are paused while Holiday Mode is active. Toggle it off to resume the schedule."
                action={<GradientButton onClick={toggleHoliday}>Resume Schedule</GradientButton>}
              />
            ) : selectedSessions.length === 0 ? (
              <EmptyState
                icon={CalendarIcon}
                title="No sessions"
                description="There are no therapy sessions planned for this day. Pick another date or book a new one."
              />
            ) : (
              <div className="space-y-3">
                <AnimatePresence>
                  {selectedSessions.map((s, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: 12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="rounded-2xl border border-neutral-100 dark:border-neutral-800 p-4 hover:shadow-md transition bg-neutral-50/60 dark:bg-neutral-800/40"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <h4 className="font-bold text-sm text-neutral-900 dark:text-white leading-snug">{s.title}</h4>
                        <Badge color={STATUS_BADGE[s.status]}>{s.status}</Badge>
                      </div>
                      <div className="space-y-1.5 text-xs text-neutral-500 dark:text-neutral-400">
                        <div className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> {s.time}</div>
                        <div className="flex items-center gap-1.5">
                          {s.mode === 'video' ? <Video className="w-3.5 h-3.5" /> : <MapPin className="w-3.5 h-3.5" />}
                          {s.mode === 'video' ? 'Video Call' : 'In-person Clinic'}
                        </div>
                        <div className="flex items-center gap-1.5"><Dot className="w-3.5 h-3.5" /> {s.therapist}</div>
                      </div>
                      {s.status === 'upcoming' && (
                        <GradientButton
                          onClick={() => toggleReminder(s)}
                          className="w-full mt-3 !py-2"
                        >
                          {reminders.has(`${year}-${month}-${selectedDay}-${s.title}`) ? 'Remove Reminder' : 'Set Reminder'}
                        </GradientButton>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}

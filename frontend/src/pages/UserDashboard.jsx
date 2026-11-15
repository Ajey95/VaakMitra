import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { Star, Target, TrendingUp, Award, Home, Zap, Calendar } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { progressAPI } from '../services/api'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, StatCard, SectionTitle } from '../components/ui'

export default function UserDashboard() {
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const { data: summary } = useQuery({
    queryKey: ['progress-summary', user?.email],
    queryFn: () => progressAPI.getProgressSummary(user?.email),
    enabled: !!user?.email,
  })

  const lessons = [
    { id: 1, symbol: 'அ', english: 'A', type: 'letter', difficulty: 1, color: 'from-blue-500 to-indigo-600' },
    { id: 2, symbol: 'ஆ', english: 'AA', type: 'letter', difficulty: 1, color: 'from-purple-500 to-violet-600' },
    { id: 3, symbol: 'ல', english: 'LA', type: 'letter', difficulty: 2, color: 'from-emerald-500 to-teal-600' },
    { id: 4, symbol: 'த', english: 'TA', type: 'letter', difficulty: 2, color: 'from-orange-500 to-red-600' },
    { id: 5, symbol: 'அம்மா', english: 'AMMA', type: 'word', difficulty: 3, color: 'from-pink-500 to-rose-600' },
    { id: 6, symbol: 'அப்பா', english: 'APPA', type: 'word', difficulty: 3, color: 'from-cyan-500 to-blue-600' },
  ]

  const getLessonStatus = (lessonId) => {
    const progress = summary?.data?.progress_by_lesson?.find((p) => p.lesson_id === lessonId)
    if (progress?.completed) return 'completed'
    if (progress?.attempts > 0) return 'in-progress'
    return 'unlocked'
  }

  const quotes = [
    'Every voice matters. Every sound is progress.',
    'Small steps lead to big achievements.',
    'Practice makes progress, not perfection.',
    "Your child's voice is a gift to the world.",
  ]
  const todayQuote = quotes[new Date().getDay() % quotes.length]

  return (
    <DashboardLayout
      title={`Welcome back, ${user?.child_name || 'friend'}!`}
      subtitle="Let's continue your speech therapy journey today"
      icon={Home}
      actions={
        <div className="flex items-center gap-2 bg-white/15 backdrop-blur px-4 py-2 rounded-full text-white text-sm font-medium">
          <Calendar className="w-4 h-4" />
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
        </div>
      }
    >
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <StatCard icon={Star} title="Total Stars" value={user?.total_stars || 0} color="gold" delay={0} />
        <StatCard icon={Target} title="Sessions" value={user?.total_sessions || 0} color="secondary" delay={0.1} />
        <StatCard icon={TrendingUp} title="Avg Accuracy" value={`${Math.round(summary?.data?.avg_accuracy || 0)}%`} color="primary" delay={0.2} />
        <StatCard icon={Award} title="Completed" value={`${summary?.data?.completed_lessons || 0}/6`} color="accent" delay={0.3} />
      </div>

      {/* Progress chart */}
      {summary?.data?.chart_data?.length > 0 && (
        <Card delay={0.3} className="p-8 mb-8">
          <SectionTitle title="Progress Over Time" subtitle="Your accuracy across recent sessions" icon={TrendingUp} />
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={summary.data.chart_data}>
              <defs>
                <linearGradient id="colorAccuracy" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" strokeOpacity={0.4} />
              <XAxis dataKey="date" stroke="#a3a3a3" fontSize={12} />
              <YAxis stroke="#a3a3a3" fontSize={12} />
              <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 25px rgba(0,0,0,0.1)' }} />
              <Area type="monotone" dataKey="accuracy" stroke="#4F46E5" strokeWidth={3} fill="url(#colorAccuracy)" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Lessons */}
      <Card delay={0.4} className="p-8 mb-8">
        <SectionTitle
          title="Your Lessons"
          icon={Star}
          action={<span className="text-sm text-neutral-500 dark:text-neutral-400">{summary?.data?.completed_lessons || 0} of 6 completed</span>}
        />
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {lessons.map((lesson, i) => {
            const status = getLessonStatus(lesson.id)
            const progress = summary?.data?.progress_by_lesson?.find((p) => p.lesson_id === lesson.id)
            return (
              <motion.div
                key={lesson.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.08 }}
                whileHover={{ y: -4, scale: 1.02 }}
                className={`relative rounded-2xl p-6 border-2 cursor-pointer transition-all duration-300 overflow-hidden ${
                  status === 'completed'
                    ? 'border-accent-300 bg-accent-50/50 dark:border-accent-700 dark:bg-accent-900/20'
                    : status === 'in-progress'
                    ? 'border-primary-300 bg-primary-50/50 dark:border-primary-700 dark:bg-primary-900/20'
                    : 'border-neutral-200 bg-white hover:border-primary-200 dark:border-neutral-700 dark:bg-neutral-800'
                }`}
                onClick={() => navigate(`/therapy/${lesson.id}`)}
              >
                <div className="absolute top-3 right-3">
                  {status === 'completed' && <span className="text-lg">✅</span>}
                  {status === 'in-progress' && (
                    <span className="flex items-center gap-1 text-xs font-semibold text-primary-600 bg-primary-100 px-2 py-1 rounded-full">
                      <Zap className="w-3 h-3" />In Progress
                    </span>
                  )}
                  {status === 'unlocked' && <span className="text-lg">🎯</span>}
                </div>

                <div className={`tamil-letter text-4xl font-bold bg-gradient-to-br ${lesson.color} bg-clip-text text-transparent mb-3`}>
                  {lesson.symbol}
                </div>

                <div className="text-xl font-bold text-neutral-900 dark:text-white mb-1">{lesson.english}</div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400 capitalize mb-3">{lesson.type} • Difficulty {lesson.difficulty}</div>

                <div className="flex gap-0.5 mb-4">
                  {[...Array(3)].map((_, j) => (
                    <Star key={j} className={`w-4 h-4 ${j < lesson.difficulty ? 'text-gold-400 fill-gold-400' : 'text-neutral-200 dark:text-neutral-700'}`} />
                  ))}
                </div>

                {progress && (
                  <div className="flex items-center gap-3 text-xs mb-4">
                    <span className="text-neutral-500 dark:text-neutral-400">Best: <span className="font-bold text-primary-600">{Math.round(progress.best_accuracy)}%</span></span>
                    <span className="text-neutral-500 dark:text-neutral-400">Stars: <span className="font-bold text-gold-600">{progress.stars_best}⭐</span></span>
                  </div>
                )}

                <button
                  className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-all ${
                    status === 'completed'
                      ? 'bg-accent-100 text-accent-700 hover:bg-accent-200'
                      : 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-md hover:shadow-lg'
                  }`}
                >
                  {status === 'completed' ? 'Review' : status === 'in-progress' ? 'Continue' : 'Start Lesson'}
                </button>
              </motion.div>
            )
          })}
        </div>
      </Card>

      {/* Quote */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="bg-gradient-to-r from-primary-600 via-primary-700 to-secondary-700 text-white rounded-3xl p-8 text-center shadow-xl relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-grid opacity-5" />
        <div className="relative z-10">
          <div className="text-5xl mb-4">💫</div>
          <p className="text-2xl font-bold mb-2">"{todayQuote}"</p>
          <p className="text-white/60 text-sm">Daily Motivation — Keep practicing every day!</p>
        </div>
      </motion.div>
    </DashboardLayout>
  )
}

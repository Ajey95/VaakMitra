import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ArrowLeft, TrendingUp, CheckCircle2, Clock, Star, Award, Target, BookOpen, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { progressAPI } from '../services/api'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function ProgressPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  
  const { data: summary } = useQuery({
    queryKey: ['progress-summary', user?.email],
    queryFn: () => progressAPI.getProgressSummary(user?.email)
  })
  
  const lessons = [
    { id: 1, symbol: 'அ', english: 'A', type: 'letter', color: 'from-blue-500 to-indigo-600' },
    { id: 2, symbol: 'ஆ', english: 'AA', type: 'letter', color: 'from-purple-500 to-violet-600' },
    { id: 3, symbol: 'ல', english: 'LA', type: 'letter', color: 'from-emerald-500 to-teal-600' },
    { id: 4, symbol: 'த', english: 'TA', type: 'letter', color: 'from-orange-500 to-red-600' },
    { id: 5, symbol: 'அம்மா', english: 'AMMA', type: 'word', color: 'from-pink-500 to-rose-600' },
    { id: 6, symbol: 'அப்பா', english: 'APPA', type: 'word', color: 'from-cyan-500 to-blue-600' },
  ]
  
  const stats = [
    { icon: Star, title: 'Total Stars', value: user?.total_stars || 0, gradient: 'from-gold-400 to-amber-500', bg: 'bg-amber-50', border: 'border-amber-100' },
    { icon: TrendingUp, title: 'Avg Accuracy', value: `${Math.round(summary?.data?.avg_accuracy || 0)}%`, gradient: 'from-primary-500 to-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-100' },
    { icon: CheckCircle2, title: 'Completed', value: `${summary?.data?.completed_lessons || 0}/6`, gradient: 'from-accent-500 to-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100' },
    { icon: Clock, title: 'Total Sessions', value: user?.total_sessions || 0, gradient: 'from-secondary-500 to-cyan-600', bg: 'bg-cyan-50', border: 'border-cyan-100' },
  ]
  
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 transition-colors">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 via-primary-700 to-secondary-700 text-white py-8 px-8 shadow-xl relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-5" />
        <div className="max-w-7xl mx-auto flex items-center gap-4 relative z-10">
          <button onClick={() => navigate('/dashboard')} className="p-2.5 hover:bg-white/10 rounded-xl transition">
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-3xl font-bold">Progress Report</h1>
            <p className="text-white/70 text-sm mt-1">Track {user?.child_name}'s speech therapy journey and achievements</p>
          </div>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto p-8">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-5 mb-8">
          {stats.map((stat, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              whileHover={{ y: -4 }}
              className={`${stat.bg} rounded-2xl p-6 border ${stat.border} hover:shadow-lg transition-all duration-300`}
            >
              <div className={`w-12 h-12 bg-gradient-to-br ${stat.gradient} rounded-xl flex items-center justify-center mb-4 shadow-md`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="text-3xl font-bold text-neutral-900 dark:text-white mb-1">{stat.value}</div>
              <div className="text-sm text-neutral-500 dark:text-neutral-400">{stat.title}</div>
            </motion.div>
          ))}
        </div>
        
        {/* Progress Chart */}
        {summary?.data?.chart_data && summary.data.chart_data.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white dark:bg-neutral-900 rounded-3xl shadow-md p-8 mb-8 border border-neutral-100 dark:border-neutral-800"
          >
            <h2 className="text-xl font-bold text-neutral-900 dark:text-white mb-6">Accuracy Over Time</h2>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={summary.data.chart_data}>
                <defs>
                  <linearGradient id="progressGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" stroke="#a3a3a3" fontSize={12} />
                <YAxis stroke="#a3a3a3" fontSize={12} />
                <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 25px rgba(0,0,0,0.1)' }} />
                <Area type="monotone" dataKey="accuracy" stroke="#4F46E5" strokeWidth={3} fill="url(#progressGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>
        )}
        
        {/* Lesson Progress */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white dark:bg-neutral-900 rounded-3xl shadow-md p-8 border border-neutral-100 dark:border-neutral-800"
        >
          <h2 className="text-xl font-bold text-neutral-900 dark:text-white mb-6">Lesson Progress</h2>
          <div className="space-y-4">
            {lessons.map((lesson, i) => {
              const progress = summary?.data?.progress_by_lesson?.find(p => p.lesson_id === lesson.id)
              const accuracy = progress?.best_accuracy || 0
              
              return (
                <motion.div
                  key={lesson.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + i * 0.08 }}
                  className="border-2 border-neutral-100 dark:border-neutral-800 rounded-2xl p-6 hover:border-primary-200 hover:shadow-md transition-all duration-300"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <div className={`w-14 h-14 bg-gradient-to-br ${lesson.color} rounded-2xl flex items-center justify-center shadow-md`}>
                        <span className="tamil-letter text-2xl font-bold text-white">{lesson.symbol}</span>
                      </div>
                      <div>
                        <div className="font-bold text-lg text-neutral-900 dark:text-white">{lesson.english}</div>
                        <div className="text-sm text-neutral-500 dark:text-neutral-400 capitalize">{lesson.type}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      {progress?.completed ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent-100 text-accent-700 font-semibold text-xs">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Completed
                        </span>
                      ) : progress?.attempts > 0 ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-100 text-primary-700 font-semibold text-xs">
                          <Zap className="w-3.5 h-3.5" /> In Progress
                        </span>
                      ) : (
                        <span className="text-neutral-400 dark:text-neutral-400 text-sm">Not Started</span>
                      )}
                    </div>
                  </div>
                  
                  {progress && (
                    <>
                      {/* Progress bar */}
                      <div className="w-full h-2.5 bg-neutral-100 dark:bg-neutral-800 rounded-full mb-4 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${accuracy}%` }}
                          transition={{ duration: 1, delay: 0.5 + i * 0.1 }}
                          className={`h-full bg-gradient-to-r ${lesson.color} rounded-full`}
                        />
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-center">
                        <div className="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-3 border border-neutral-100 dark:border-neutral-800">
                          <div className="text-xl font-bold text-neutral-900 dark:text-white">{progress.attempts}</div>
                          <div className="text-xs text-neutral-500 dark:text-neutral-400">Attempts</div>
                        </div>
                        <div className="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-3 border border-neutral-100 dark:border-neutral-800">
                          <div className="text-xl font-bold text-primary-600">{Math.round(progress.best_accuracy)}%</div>
                          <div className="text-xs text-neutral-500 dark:text-neutral-400">Best Score</div>
                        </div>
                        <div className="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-3 border border-neutral-100 dark:border-neutral-800">
                          <div className="text-xl font-bold text-gold-600">{progress.stars_earned || progress.stars_best || 0}</div>
                          <div className="text-xs text-neutral-500 dark:text-neutral-400">Stars Earned</div>
                        </div>
                      </div>
                    </>
                  )}
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Mic, Activity, Volume2, Wind, Lightbulb, TrendingUp, Target, Play,
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, ProgressRing, Badge, GradientButton } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { analysisAPI } from '../services/api'

const METRIC_DEFS = [
  { key: 'accuracy', label: 'Pronunciation', icon: Volume2, color: 'from-primary-500 to-indigo-600' },
  { key: 'clarity', label: 'Clarity (GOP)', icon: Activity, color: 'from-secondary-500 to-cyan-600' },
  { key: 'sound_match', label: 'Sound Match (MFCC)', icon: Target, color: 'from-gold-400 to-amber-500' },
  { key: 'airflow', label: 'Breath / Airflow', icon: Wind, color: 'from-accent-500 to-emerald-600' },
]

function statusFor(score) {
  if (score >= 90) return { label: 'Excellent', color: 'accent' }
  if (score >= 75) return { label: 'Good', color: 'primary' }
  if (score >= 50) return { label: 'Fair', color: 'gold' }
  return { label: 'Needs work', color: 'coral' }
}

function MetricBar({ label, value, color, icon: Icon, delay }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-neutral-400" />
          <span className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">{label}</span>
        </div>
        <span className="text-sm font-bold text-neutral-900 dark:text-white">{Math.round(value)}%</span>
      </div>
      <div className="h-2.5 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
        <motion.div
          className={`h-full rounded-full bg-gradient-to-r ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 1, delay, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

export default function SpeechAnalysisPage() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    analysisAPI
      .getAnalysis('me')
      .then((res) => alive && setData(res.data))
      .catch(() => alive && setError(true))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  const hasData = data?.has_data

  return (
    <DashboardLayout
      title="Speech Analysis"
      subtitle={`Pronunciation insights for ${user?.child_name || user?.full_name || 'your child'}`}
      icon={Mic}
    >
      <div className="space-y-6">
        {/* CTA: real practice (recording lives in the therapy flow) */}
        <Card className="p-8 overflow-hidden relative">
          <div className="absolute -top-16 -right-16 w-56 h-56 bg-primary-500/10 rounded-full blur-3xl" />
          <div className="relative z-10 flex flex-col items-center text-center">
            <Badge color="primary" className="mb-4">
              <Mic className="w-3 h-3" /> Live speech feedback
            </Badge>
            <h2 className="text-xl font-bold text-neutral-900 dark:text-white mb-1">
              Practice to improve your scores
            </h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 max-w-md mb-6">
              Start a therapy session to record your voice and get real-time, syllable-level
              pronunciation feedback. Every session updates the analytics below.
            </p>
            <GradientButton onClick={() => navigate('/training')}>
              <Play className="w-4 h-4" /> Start a practice session
            </GradientButton>
          </div>
        </Card>

        {loading && <div className="text-center py-12 text-neutral-400">Loading your analysis…</div>}

        {error && !loading && (
          <Card className="p-4 border-coral-200 bg-coral-50/60">
            <p className="text-sm text-coral-700">Couldn&apos;t load your analysis. Please try again later.</p>
          </Card>
        )}

        {!loading && !error && !hasData && (
          <Card className="p-10 text-center">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-primary-50 flex items-center justify-center mb-4">
              <TrendingUp className="w-8 h-8 text-primary-500" />
            </div>
            <h3 className="font-bold text-lg text-neutral-900 dark:text-white mb-1">No analysis yet</h3>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Complete your first practice session and your pronunciation insights will appear here.
            </p>
          </Card>
        )}

        {!loading && hasData && (
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            {/* Overall + metrics */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="p-8 flex flex-col items-center justify-center text-center">
                <SectionTitle title="Overall Accuracy" />
                <ProgressRing value={Math.round(data.overall)} size={150} stroke={12} color="#4F46E5" sublabel="avg accuracy" />
                <Badge color="neutral" className="mt-4">{data.total_attempts} sessions analysed</Badge>
              </Card>

              <Card className="p-8 lg:col-span-2">
                <SectionTitle title="Voice Metrics" subtitle="Averaged across your sessions" icon={Activity} />
                <div className="space-y-5">
                  {METRIC_DEFS.map((m, i) => (
                    <MetricBar key={m.key} label={m.label} value={data.metrics[m.key] || 0} color={m.color} icon={m.icon} delay={i * 0.12} />
                  ))}
                </div>
              </Card>
            </div>

            {/* Phoneme + chart */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="p-8">
                <SectionTitle title="Sound Breakdown" subtitle="Average accuracy per word/letter" icon={Volume2} />
                <div className="space-y-3">
                  {data.by_phoneme.map((p, i) => {
                    const st = statusFor(p.accuracy)
                    return (
                      <motion.div
                        key={p.phoneme}
                        initial={{ opacity: 0, x: -16 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.08 }}
                        className="flex items-center gap-4 p-3 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50"
                      >
                        <div className="w-14 h-12 rounded-xl bg-white dark:bg-neutral-900 border border-neutral-100 dark:border-neutral-700 flex items-center justify-center font-bold text-primary-600 dark:text-primary-400">
                          {p.phoneme}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <Badge color={st.color}>{st.label}</Badge>
                            <span className="text-sm font-bold text-neutral-800 dark:text-neutral-100">{Math.round(p.accuracy)}% · {p.attempts}×</span>
                          </div>
                          <div className="h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                            <motion.div
                              className={`h-full rounded-full bg-gradient-to-r ${
                                st.color === 'accent' ? 'from-accent-500 to-emerald-500'
                                  : st.color === 'primary' ? 'from-primary-500 to-indigo-500'
                                  : st.color === 'gold' ? 'from-gold-400 to-amber-500'
                                  : 'from-coral-500 to-rose-500'
                              }`}
                              initial={{ width: 0 }}
                              animate={{ width: `${p.accuracy}%` }}
                              transition={{ duration: 0.9, delay: i * 0.08 }}
                            />
                          </div>
                        </div>
                      </motion.div>
                    )
                  })}
                </div>
              </Card>

              <Card className="p-8">
                <SectionTitle title="Accuracy Trend" subtitle="Your recent sessions" icon={TrendingUp} />
                <div className="h-64">
                  {data.history.length > 1 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={data.history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.4} />
                        <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                        <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 8px 30px rgba(0,0,0,0.12)' }} />
                        <Line type="monotone" dataKey="accuracy" stroke="#06b6d4" strokeWidth={3} dot={{ r: 4, fill: '#06b6d4' }} activeDot={{ r: 6 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-sm text-neutral-400">
                      Practice a few more sessions to see your trend.
                    </div>
                  )}
                </div>
              </Card>
            </div>

            {/* Suggestion from the weakest sound */}
            {data.weakest && (
              <Card className="p-8">
                <SectionTitle title="Suggestion" subtitle="Based on your lowest-scoring sound" icon={Lightbulb} />
                <div className="flex items-start gap-4 p-5 rounded-2xl border border-neutral-100 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-800/50">
                  <div className="w-11 h-11 rounded-xl flex items-center justify-center bg-gradient-to-br from-gold-400 to-amber-500 shrink-0">
                    <Lightbulb className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h4 className="font-bold text-neutral-900 dark:text-white mb-1">
                      Focus on &quot;{data.weakest.phoneme}&quot; ({Math.round(data.weakest.accuracy)}%)
                    </h4>
                    <p className="text-sm text-neutral-500 dark:text-neutral-400">
                      This is your lowest-scoring sound so far. Try a few focused sessions on it — listen to
                      the example, watch the mouth movement, and practice slowly.
                    </p>
                    <div className="mt-4">
                      <GradientButton onClick={() => navigate('/training')}>
                        <Play className="w-4 h-4" /> Practice this sound
                      </GradientButton>
                    </div>
                  </div>
                </div>
              </Card>
            )}
          </motion.div>
        )}
      </div>
    </DashboardLayout>
  )
}

import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  GraduationCap, BookOpen, Video, ScanFace, Mic, ArrowRight, Play,
  Circle, Lock, Sparkles, Flame, Clock, Star,
} from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, ProgressRing, Badge, GradientButton } from '../components/ui'
import { therapyAPI } from '../services/api'
import { buildLessonRoadmap } from '../features/curriculum/lessonRoadmap'

const MODULES = [
  {
    id: 'letter',
    icon: BookOpen,
    title: 'Letter & Picture',
    desc: 'Learn Tamil letters paired with familiar pictures to build recognition.',
    progress: 80,
    color: 'from-primary-500 to-indigo-600',
    ring: '#4F46E5',
    path: '/letter-learning',
  },
  {
    id: 'video',
    icon: Video,
    title: 'Training Video',
    desc: 'Watch a guided demonstration of how each sound is formed.',
    progress: 100,
    color: 'from-secondary-500 to-cyan-600',
    ring: '#06B6D4',
    path: '/videos',
  },
  {
    id: 'tongue',
    icon: ScanFace,
    title: 'Tongue Movement',
    desc: 'Camera-based evaluation of tongue and mouth articulation.',
    progress: 55,
    color: 'from-accent-500 to-emerald-600',
    ring: '#10B981',
    path: '/tongue-tracking',
  },
  {
    id: 'speech',
    icon: Mic,
    title: 'Speech Accuracy',
    desc: 'Pronounce the sound and get an instant accuracy score.',
    progress: 40,
    color: 'from-gold-400 to-amber-500',
    ring: '#F59E0B',
    path: '/speech-analysis',
  },
]

const LESSON_STATUS = {
  teaching: { icon: BookOpen, color: 'text-secondary-500', badge: 'primary', label: 'Teaching only', cta: 'Learn' },
  available: { icon: Circle, color: 'text-primary-500', badge: 'primary', label: 'Available', cta: 'Start' },
  preparing: { icon: Clock, color: 'text-gold-500', badge: 'gold', label: 'Evidence pending', cta: 'Preparing' },
}

export default function TrainingPage() {
  const navigate = useNavigate()
  const overall = Math.round(MODULES.reduce((a, m) => a + m.progress, 0) / MODULES.length)
  const { data: lessonResponse, isLoading, isError } = useQuery({
    queryKey: ['therapy-lessons'],
    queryFn: therapyAPI.getLessons,
    retry: false,
  })
  const lessons = buildLessonRoadmap(lessonResponse?.data)
  const recommended = lessons.find((lesson) => lesson.canScore) || lessons.find((lesson) => lesson.canOpen)

  return (
    <DashboardLayout title="Training Hub" subtitle="Your 4-in-1 Tamil therapy journey" icon={GraduationCap}>
      {/* Hero */}
      <Card className="overflow-hidden mb-8 bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 text-white border-0">
        <div className="p-8 relative flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="absolute -right-10 -top-10 w-52 h-52 bg-white/10 rounded-full blur-3xl" />
          <div className="relative max-w-xl">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5" />
              <span className="text-sm font-semibold uppercase tracking-wider text-white/80">How training works</span>
            </div>
            <h2 className="text-2xl font-bold mb-2">Four steps to confident Tamil speech</h2>
            <p className="text-white/80 text-sm leading-relaxed">
              Each lesson flows through four connected modules — learn the letter, watch a demo,
              practice tongue movement, and finish with a speech-accuracy check. Complete all four to earn your stars.
            </p>
          </div>
          <div className="relative shrink-0 text-center">
            <ProgressRing value={overall} color="#FFFFFF" label={`${overall}%`} sublabel="Overall" />
            <p className="text-xs text-white/70 mt-2">Module completion</p>
          </div>
        </div>
      </Card>

      {/* Module cards */}
      <SectionTitle title="The 4-in-1 Module" subtitle="Tap any step to jump in" icon={GraduationCap} />
      <div className="grid sm:grid-cols-2 gap-5 mb-10">
        {MODULES.map((m, i) => (
          <motion.div
            key={m.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            whileHover={{ y: -4 }}
            className="bg-white dark:bg-neutral-900 rounded-3xl border border-neutral-100 dark:border-neutral-800 shadow-md hover:shadow-lg transition overflow-hidden"
          >
            <div className={`h-2 bg-gradient-to-r ${m.color}`} />
            <div className="p-6 flex items-center gap-5">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-bold text-neutral-400 uppercase tracking-wide">Step {i + 1}</span>
                </div>
                <div className={`w-12 h-12 bg-gradient-to-br ${m.color} rounded-xl flex items-center justify-center mb-3 shadow-md`}>
                  <m.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-bold text-lg text-neutral-900 dark:text-white">{m.title}</h3>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1 mb-4">{m.desc}</p>
                <GradientButton onClick={() => navigate(m.path)}>
                  <Play className="w-4 h-4" /> {m.progress === 100 ? 'Replay' : m.progress > 0 ? 'Continue' : 'Start'}
                </GradientButton>
              </div>
              <div className="shrink-0">
                <ProgressRing value={m.progress} size={88} stroke={8} color={m.ring} sublabel="done" />
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Recommended session */}
      {recommended && <Card className="overflow-hidden mb-10 bg-gradient-to-r from-accent-500 to-emerald-600 text-white border-0">
        <div className="p-6 flex flex-col sm:flex-row items-center justify-between gap-4 relative">
          <div className="absolute -right-8 -bottom-8 w-40 h-40 bg-white/10 rounded-full blur-2xl" />
          <div className="relative flex items-center gap-4">
            <div className="w-14 h-14 bg-white/20 backdrop-blur rounded-2xl flex items-center justify-center text-3xl font-bold shrink-0">
              {recommended.letter}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Flame className="w-4 h-4" />
                <span className="text-sm font-semibold uppercase tracking-wider text-white/80">Today's recommended session</span>
              </div>
              <h3 className="text-xl font-bold">Lesson {recommended.id} · {recommended.letter} ({recommended.roman})</h3>
              <p className="text-white/80 text-sm mt-0.5">{recommended.statusDetail}</p>
            </div>
          </div>
          <button
            onClick={() => navigate(`/therapy/${recommended.id}`)}
            className="relative inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-accent-700 font-bold text-sm shadow-md hover:shadow-lg hover:scale-105 transition shrink-0"
          >
            {recommended.canScore ? 'Start word practice' : 'Open teaching activity'} <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </Card>}

      {/* Lesson roadmap */}
      <SectionTitle title="Tamil Lesson Roadmap" subtitle={`${lessons.length} server-owned lessons from letters to functional words`} icon={BookOpen} />
      <Card className="p-4 sm:p-6">
        {isLoading && <p className="p-4 text-neutral-500">Loading the approved curriculum…</p>}
        {isError && <p className="p-4 text-red-600">The curriculum is unavailable. No fallback lessons were substituted.</p>}
        {!isLoading && !isError && lessons.length === 0 && (
          <p className="p-4 text-neutral-500">No curriculum is currently available.</p>
        )}
        <div className="space-y-3">
          {lessons.map((l, i) => {
            const st = LESSON_STATUS[l.status]
            const locked = !l.canOpen
            return (
              <motion.div
                key={l.id}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-center gap-4 p-3 rounded-2xl border border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition"
              >
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-bold shrink-0 ${
                  locked
                    ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-300 dark:text-neutral-600'
                    : 'bg-gradient-to-br from-primary-500 to-secondary-500 text-white shadow-md'
                }`}>
                  {l.letter}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-bold text-neutral-900 dark:text-white">Lesson {l.id} · {l.roman}</h4>
                    <Badge color={st.badge}>{st.label}</Badge>
                  </div>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 flex items-center gap-1.5">
                    <st.icon className={`w-3.5 h-3.5 ${st.color}`} />
                    {l.statusDetail}
                  </p>
                </div>
                <button
                  onClick={() => !locked && navigate(`/therapy/${l.id}`)}
                  disabled={locked}
                  className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold transition shrink-0 ${
                    locked
                      ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 cursor-not-allowed'
                      : 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/50'
                  }`}
                >
                  {locked ? <Lock className="w-4 h-4" /> : <Play className="w-4 h-4" />} {st.cta}
                </button>
              </motion.div>
            )
          })}
        </div>
      </Card>
    </DashboardLayout>
  )
}

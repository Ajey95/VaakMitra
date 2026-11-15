import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Info, Target, BookOpen, Mic, Eye, Trophy, HeartHandshake,
  Code2, Server, ShieldCheck, Brain, Database, Cloud, Sparkles,
  Users, GraduationCap, ArrowRight, Rocket, CheckCircle2, Circle, Clock,
} from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, StatCard, SectionTitle, Badge, GradientButton } from '../components/ui'

const FEATURES = [
  { icon: BookOpen, title: 'Letter & Picture Learning', desc: 'Interactive Tamil letters paired with pictures to build recognition.', color: 'from-primary-500 to-indigo-600' },
  { icon: Mic, title: 'Tamil Word Check', desc: 'Local PASS, RETRY or UNSCORABLE feedback for an assigned Tamil word.', color: 'from-secondary-500 to-cyan-600' },
  { icon: Eye, title: 'Optional Visual Guide', desc: 'A copy-along mouth guide that is never clinical or word-scoring evidence.', color: 'from-accent-500 to-emerald-600' },
  { icon: Trophy, title: 'Rewards & Motivation', desc: 'Stars, streaks and games keep children engaged session after session.', color: 'from-gold-400 to-amber-500' },
]

const STACK = [
  { icon: Code2, label: 'React', sub: 'Frontend UI' },
  { icon: Server, label: 'FastAPI', sub: 'Backend API' },
  { icon: ShieldCheck, label: 'Fail Closed', sub: 'Explicit UNSCORABLE state' },
  { icon: Brain, label: 'IndicConformer', sub: 'Local Tamil baseline' },
  { icon: Database, label: 'Encrypted Store', sub: 'Minimum metrics only' },
  { icon: Cloud, label: 'Vite + Tailwind', sub: 'Build & styling' },
]

const TEAM = [
  { name: 'Nitin Gupta', role: 'Full-Stack & ML', initial: 'N' },
  { name: 'Team Member 2', role: 'Frontend & UX', initial: 'A' },
  { name: 'Team Member 3', role: 'Speech & Media', initial: 'S' },
  { name: 'Team Member 4', role: 'Backend & Data', initial: 'K' },
]

const ROADMAP = [
  { phase: 'Phase 1', title: 'Research & Tamil curriculum design', status: 'done' },
  { phase: 'Phase 2', title: '4-in-1 therapy module & dashboard', status: 'done' },
  { phase: 'Phase 3', title: 'Therapist hub & appointment system', status: 'progress' },
  { phase: 'Phase 4', title: 'Multi-language expansion & analytics', status: 'planned' },
]

const STATUS = {
  done: { icon: CheckCircle2, color: 'text-accent-500', badge: 'accent', label: 'Completed' },
  progress: { icon: Clock, color: 'text-gold-500', badge: 'gold', label: 'In Progress' },
  planned: { icon: Circle, color: 'text-neutral-400', badge: 'neutral', label: 'Planned' },
}

export default function AboutPage() {
  const navigate = useNavigate()

  return (
    <DashboardLayout title="About SpeakEasy ASD" subtitle="Our mission, technology and team" icon={Info}>
      {/* Hero / mission */}
      <Card className="overflow-hidden mb-8 bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 text-white border-0">
        <div className="p-8 sm:p-10 relative">
          <div className="absolute -right-10 -top-10 w-52 h-52 bg-white/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-grid opacity-5" />
          <div className="relative max-w-2xl">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-5 h-5" />
              <span className="text-sm font-semibold uppercase tracking-wider text-white/80">Our Mission</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold leading-snug mb-3">
              Making supervised Tamil word practice calm, private and engaging.
            </h2>
            <p className="text-white/80 text-sm sm:text-base leading-relaxed">
              VaakMitra combines play and local speech intelligence to support word practice for autistic
              children aged 7–14. It is an assistive technical prototype, not a diagnosis or therapist replacement.
            </p>
          </div>
        </div>
      </Card>

      {/* What we do */}
      <SectionTitle title="What We Do" subtitle="Four connected modules, one gentle journey" icon={Sparkles} />
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            whileHover={{ y: -4 }}
            className="bg-white dark:bg-neutral-900 rounded-2xl p-5 border border-neutral-100 dark:border-neutral-800 shadow-md hover:shadow-lg transition"
          >
            <div className={`w-12 h-12 bg-gradient-to-br ${f.color} rounded-xl flex items-center justify-center mb-4 shadow-md`}>
              <f.icon className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-bold text-neutral-900 dark:text-white text-sm mb-1">{f.title}</h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">{f.desc}</p>
          </motion.div>
        ))}
      </div>

      {/* Stats band */}
      <div className="grid sm:grid-cols-3 gap-4 mb-10">
        <StatCard icon={Users} title="Target age" value="7–14" sub="therapist-supervised use" color="primary" delay={0} />
        <StatCard icon={Mic} title="Assessment level" value="Word" sub="no production phoneme scoring" color="secondary" delay={0.05} />
        <StatCard icon={Target} title="Safe outcomes" value="3" sub="PASS · RETRY · UNSCORABLE" color="accent" delay={0.1} />
      </div>

      {/* Tech stack */}
      <SectionTitle title="Technology Stack" subtitle="Built with a modern, privacy-first toolkit" icon={Code2} />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-10">
        {STACK.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            whileHover={{ y: -3 }}
            className="flex items-center gap-3 bg-white dark:bg-neutral-900 rounded-2xl p-4 border border-neutral-100 dark:border-neutral-800 shadow-sm"
          >
            <div className="w-11 h-11 rounded-xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center shrink-0">
              <s.icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div className="min-w-0">
              <div className="font-bold text-sm text-neutral-900 dark:text-white">{s.label}</div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400 truncate">{s.sub}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Team */}
      <SectionTitle title="The Team" subtitle="Team 96 · Amrita Vishwa Vidyapeetham" icon={GraduationCap} />
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {TEAM.map((m, i) => (
          <motion.div
            key={m.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            whileHover={{ y: -4 }}
            className="bg-white dark:bg-neutral-900 rounded-2xl p-5 border border-neutral-100 dark:border-neutral-800 shadow-md text-center"
          >
            <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-2xl font-bold shadow-md mb-3">
              {m.initial}
            </div>
            <h3 className="font-bold text-neutral-900 dark:text-white text-sm">{m.name}</h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">{m.role}</p>
          </motion.div>
        ))}
      </div>

      {/* Roadmap */}
      <SectionTitle title="Roadmap" subtitle="Where we've been and where we're going" icon={Rocket} />
      <Card className="p-6 mb-8">
        <div className="space-y-1">
          {ROADMAP.map((r, i) => {
            const st = STATUS[r.status]
            return (
              <div key={r.phase} className="flex items-start gap-4 relative">
                <div className="flex flex-col items-center">
                  <st.icon className={`w-6 h-6 ${st.color} shrink-0`} />
                  {i < ROADMAP.length - 1 && <div className="w-0.5 flex-1 min-h-[28px] bg-neutral-100 dark:bg-neutral-800 my-1" />}
                </div>
                <div className="pb-5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold uppercase tracking-wide text-neutral-400">{r.phase}</span>
                    <Badge color={st.badge}>{st.label}</Badge>
                  </div>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 mt-1">{r.title}</p>
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      <div id="privacy" className="scroll-mt-24 mb-8">
        <SectionTitle title="Privacy Policy" subtitle="How SpeakEasy protects families" icon={Target} />
        <Card className="p-6">
          <p className="text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
            Live camera and microphone activities are processed for the active exercise and are released when the activity ends. Raw child audio and video are not stored by Play & Practice. Account and aggregate progress requests use the secured application API.
          </p>
        </Card>
      </div>

      <div id="terms" className="scroll-mt-24 mb-8">
        <SectionTitle title="Terms of Service" subtitle="Safe and supported use" icon={BookOpen} />
        <Card className="p-6">
          <p className="text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
            SpeakEasy is a guided practice aid and does not replace diagnosis or care from a qualified speech-language professional. A parent, caregiver, or therapist should supervise child use and stop any exercise that causes discomfort.
          </p>
        </Card>
      </div>

      {/* CTA */}
      <Card className="overflow-hidden bg-gradient-to-r from-accent-500 to-emerald-600 text-white border-0">
        <div className="p-8 flex flex-col sm:flex-row items-center justify-between gap-4 relative">
          <div className="absolute -right-8 -bottom-8 w-40 h-40 bg-white/10 rounded-full blur-2xl" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-1">
              <HeartHandshake className="w-5 h-5" />
              <span className="text-sm font-semibold uppercase tracking-wider text-white/80">Get started</span>
            </div>
            <h3 className="text-xl font-bold">Ready to begin your child's journey?</h3>
            <p className="text-white/80 text-sm mt-1">Jump back to the dashboard and start today's session.</p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="relative inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-accent-700 font-bold text-sm shadow-md hover:shadow-lg hover:scale-105 transition shrink-0"
          >
            Go to Dashboard <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </Card>
    </DashboardLayout>
  )
}

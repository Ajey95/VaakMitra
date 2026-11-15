import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageSquarePlus, Star, Bug, Lightbulb, Heart, MoreHorizontal,
  Send, CheckCircle2, Sparkles, Quote, TrendingUp, PartyPopper,
} from 'lucide-react'
import toast from 'react-hot-toast'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, ProgressRing, Badge, GradientButton } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { contactAPI } from '../services/api'

const CATEGORIES = [
  { id: 'bug', label: 'Bug', icon: Bug, color: 'coral' },
  { id: 'feature', label: 'Feature', icon: Lightbulb, color: 'gold' },
  { id: 'praise', label: 'Praise', icon: Heart, color: 'accent' },
  { id: 'other', label: 'Other', icon: MoreHorizontal, color: 'neutral' },
]

const TESTIMONIALS = [
  { name: 'Meena S.', role: 'Parent', text: 'Arjun loves the candle game! His pronunciation of அ and ஆ has improved so much in 3 weeks.', rating: 5 },
  { name: 'Dr. Karthik', role: 'Speech Therapist', text: 'The tongue tracking feedback is genuinely useful for reinforcing articulation between sessions.', rating: 5 },
  { name: 'Ravi K.', role: 'Parent', text: 'Finally a Tamil-first app. The reward stars keep my daughter motivated every day.', rating: 4 },
]

const RATING_LABELS = ['', 'Poor', 'Fair', 'Good', 'Great', 'Excellent']

export default function FeedbackPage() {
  const { user } = useAuthStore()
  const [rating, setRating] = useState(0)
  const [hover, setHover] = useState(0)
  const [category, setCategory] = useState('praise')
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [sending, setSending] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!rating) { toast.error('Please pick a star rating'); return }
    if (!message.trim()) { toast.error('Please share a few words'); return }
    setSending(true)
    try {
      await contactAPI.submitContact({
        name: user?.full_name || 'Anonymous',
        email: email || user?.email,
        subject: `Feedback (${rating}★, ${category})`,
        message,
      })
      setSubmitted(true)
      toast.success('Thank you for your feedback! 🎉', { duration: 4000 })
    } catch (err) {
      toast.error('Could not send feedback. Please try again.')
    } finally {
      setSending(false)
    }
  }

  const reset = () => {
    setSubmitted(false)
    setRating(0); setHover(0); setCategory('praise'); setMessage(''); setEmail('')
  }

  return (
    <DashboardLayout title="Share Feedback" subtitle="Help us make SpeakEasy better for every child" icon={MessageSquarePlus}>
      {/* Hero */}
      <Card className="overflow-hidden mb-6 bg-gradient-to-r from-primary-500 via-primary-600 to-secondary-500 text-white border-0">
        <div className="p-8 relative">
          <div className="absolute -right-8 -top-8 w-40 h-40 bg-white/10 rounded-full blur-2xl" />
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-5 h-5" />
            <span className="text-sm font-semibold uppercase tracking-wider text-white/80">We're listening</span>
          </div>
          <h2 className="text-2xl font-bold mb-1">Your voice shapes the journey</h2>
          <p className="text-white/80 text-sm max-w-lg">Every piece of feedback helps us build a kinder, more effective therapy experience for autistic children learning Tamil.</p>
        </div>
      </Card>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Form / thank-you */}
        <div className="lg:col-span-2">
          <AnimatePresence mode="wait">
            {!submitted ? (
              <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.97 }}>
                <Card className="p-6">
                  <form onSubmit={handleSubmit} className="space-y-7">
                    {/* Star rating */}
                    <div>
                      <SectionTitle title="How would you rate your experience?" icon={Star} />
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <button
                            key={s}
                            type="button"
                            onMouseEnter={() => setHover(s)}
                            onMouseLeave={() => setHover(0)}
                            onClick={() => setRating(s)}
                            className="transition-transform hover:scale-110"
                          >
                            <Star
                              className={`w-9 h-9 transition-colors ${
                                (hover || rating) >= s ? 'text-gold-400 fill-gold-400' : 'text-neutral-200 dark:text-neutral-700'
                              }`}
                            />
                          </button>
                        ))}
                        {(hover || rating) > 0 && (
                          <span className="ml-3 text-sm font-semibold text-gold-600 dark:text-gold-400">{RATING_LABELS[hover || rating]}</span>
                        )}
                      </div>
                    </div>

                    {/* Category */}
                    <div>
                      <SectionTitle title="What's this about?" icon={MessageSquarePlus} />
                      <div className="flex flex-wrap gap-2.5">
                        {CATEGORIES.map((c) => {
                          const active = category === c.id
                          return (
                            <button
                              key={c.id}
                              type="button"
                              onClick={() => setCategory(c.id)}
                              className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold border transition ${
                                active
                                  ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white border-transparent shadow-md'
                                  : 'bg-white dark:bg-neutral-900 text-neutral-600 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700 hover:border-primary-300'
                              }`}
                            >
                              <c.icon className="w-4 h-4" /> {c.label}
                            </button>
                          )
                        })}
                      </div>
                    </div>

                    {/* Message */}
                    <div>
                      <label className="block text-sm font-bold text-neutral-800 dark:text-neutral-100 mb-2">Tell us more</label>
                      <textarea
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        rows={5}
                        placeholder="Share what you loved, what confused you, or what you'd like to see…"
                        className="w-full px-4 py-3 rounded-2xl text-sm bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 outline-none focus:ring-2 focus:ring-primary-200 text-neutral-800 dark:text-white resize-none"
                      />
                    </div>

                    {/* Email */}
                    <div>
                      <label className="block text-sm font-bold text-neutral-800 dark:text-neutral-100 mb-2">Email <span className="font-normal text-neutral-400">(optional — if you'd like a reply)</span></label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        className="w-full px-4 py-3 rounded-2xl text-sm bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 outline-none focus:ring-2 focus:ring-primary-200 text-neutral-800 dark:text-white"
                      />
                    </div>

                    <GradientButton type="submit" disabled={sending} className="w-full py-3"><Send className="w-4 h-4" /> {sending ? 'Sending…' : 'Submit Feedback'}</GradientButton>
                  </form>
                </Card>
              </motion.div>
            ) : (
              <motion.div key="thanks" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                <Card className="p-10 text-center">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1, rotate: [0, -10, 10, 0] }}
                    transition={{ type: 'spring', delay: 0.1 }}
                    className="w-20 h-20 mx-auto bg-gradient-to-br from-accent-500 to-emerald-600 rounded-3xl flex items-center justify-center shadow-lg mb-5"
                  >
                    <PartyPopper className="w-10 h-10 text-white" />
                  </motion.div>
                  <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">Thank you! 🎉</h2>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 max-w-md mx-auto mb-6">
                    Your {rating}-star feedback has been received. We read every message and use it to make therapy better for children like yours.
                  </p>
                  <div className="flex items-center justify-center gap-1 mb-6">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star key={s} className={`w-6 h-6 ${rating >= s ? 'text-gold-400 fill-gold-400' : 'text-neutral-200 dark:text-neutral-700'}`} />
                    ))}
                  </div>
                  <button onClick={reset} className="text-sm font-semibold text-primary-600 dark:text-primary-400 hover:underline">
                    Submit more feedback
                  </button>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Side panel */}
        <div className="space-y-6">
          <Card className="p-6 text-center">
            <SectionTitle title="Satisfaction" icon={TrendingUp} />
            <ProgressRing value={94} color="#10B981" label="94%" sublabel="Happy users" />
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-4">Based on 1,280 ratings this quarter</p>
            <div className="grid grid-cols-2 gap-3 mt-4">
              <div className="p-3 rounded-xl bg-neutral-50 dark:bg-neutral-800">
                <div className="text-xl font-bold text-neutral-900 dark:text-white">4.8</div>
                <div className="text-[11px] text-neutral-500">Avg rating</div>
              </div>
              <div className="p-3 rounded-xl bg-neutral-50 dark:bg-neutral-800">
                <div className="text-xl font-bold text-neutral-900 dark:text-white">2.3k</div>
                <div className="text-[11px] text-neutral-500">Reviews</div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <SectionTitle title="From the community" icon={Quote} />
            <div className="space-y-4">
              {TESTIMONIALS.map((t, i) => (
                <motion.div
                  key={t.name}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-100 dark:border-neutral-800"
                >
                  <div className="flex items-center gap-0.5 mb-2">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star key={s} className={`w-3.5 h-3.5 ${t.rating >= s ? 'text-gold-400 fill-gold-400' : 'text-neutral-200 dark:text-neutral-700'}`} />
                    ))}
                  </div>
                  <p className="text-sm text-neutral-600 dark:text-neutral-300 leading-relaxed mb-3">"{t.text}"</p>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-xs font-bold">
                      {t.name.charAt(0)}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-neutral-800 dark:text-neutral-100">{t.name}</div>
                      <Badge color="neutral" className="mt-0.5">{t.role}</Badge>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}

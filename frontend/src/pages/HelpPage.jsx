import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  HelpCircle, Search, Rocket, Video, MessageCircle, Users, ChevronDown,
  Mail, Clock, Send, BookOpen, FileText, ArrowRight, LifeBuoy,
} from 'lucide-react'
import toast from 'react-hot-toast'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, GradientButton } from '../components/ui'
import { contactAPI } from '../services/api'
import { useNavigate } from 'react-router-dom'

const QUICK_ACTIONS = [
  { icon: Rocket, title: 'Getting Started', desc: 'Set up your child profile and first session', color: 'from-primary-500 to-indigo-600', target: 'faq' },
  { icon: Video, title: 'Video Tutorials', desc: 'Watch step-by-step walkthroughs', color: 'from-secondary-500 to-cyan-600', path: '/videos' },
  { icon: MessageCircle, title: 'Contact Support', desc: 'Reach our team for direct help', color: 'from-accent-500 to-emerald-600', target: 'contact-support' },
  { icon: Users, title: 'Community', desc: 'Connect with other parents', color: 'from-gold-400 to-amber-500', path: '/parent' },
]

const FAQS = [
  { q: 'How do I start my first word-practice session?', a: 'Go to the Training hub and choose a therapist-approved Tamil lesson. The companion presents a known word, listens locally and responds gently.', tag: 'Getting Started' },
  { q: 'How does the Tamil word check work?', a: 'The edge service combines a Tamil speech model, deterministic normalization, word-level representation matching and calibrated uncertainty. It returns PASS, RETRY or UNSCORABLE; it does not show a child-facing accuracy percentage.', tag: 'Features' },
  { q: 'Is my child\'s voice private?', a: 'The child-session design keeps raw and normalized audio, transcripts and voice-derived representations on the trusted edge device and does not persist them by default. Only consented, allow-listed pseudonymous aggregates may sync.', tag: 'Privacy' },
  { q: 'Does the camera grade speech or emotion?', a: 'No. Camera, mouth-shape and facial emotion data are not part of the Tamil word decision. Optional visual copy-along activities are non-clinical.', tag: 'Features' },
  { q: 'Can I track progress over time?', a: 'Therapist and caregiver views can summarize word outcomes and attempts. These are assistive indicators, not diagnosis or proof of clinical improvement.', tag: 'Progress' },
  { q: 'Which devices and browsers are supported?', a: 'The current prototype uses a Chrome or Edge client connected to a private local GPU workstation. A microphone is required for word practice; the camera is not.', tag: 'Technical' },
  { q: 'How do I change the app language?', a: 'Open Profile → Preferences and choose between Tamil, English, and Hindi. The default Tamil curriculum remains available regardless of UI language.', tag: 'Settings' },
  { q: 'How do I reset my password?', a: 'Go to Profile → Privacy & Security → Change Password, or use the "Forgot password" link on the login screen to receive a secure reset link by email.', tag: 'Account' },
]

const ARTICLES = [
  'Setting up camera & microphone permissions',
  'Understanding the 6 Tamil lesson roadmap',
  'Reading your child\'s progress report',
  'Tips for keeping sessions calm & engaging',
  'Earning and redeeming reward stars',
]

const ARTICLE_CONTENT = {
  'Setting up camera & microphone permissions': 'Use Chrome or Edge, open the lock icon beside the address, allow Camera and Microphone, then reload the activity. You can always choose the camera-free or screen-control option.',
  'Understanding the 6 Tamil lesson roadmap': 'Open Training, choose a lesson, and move through the picture, demonstration, movement practice, speech check, and reward steps at your child’s pace.',
  'Reading your child\'s progress report': 'Progress shows completed lessons and current totals. Reports groups the available speech and practice data by time period without inventing missing results.',
  'Tips for keeping sessions calm & engaging': 'Keep sessions short, use Calm mode, allow breaks, and celebrate attempts. A child can pause or use supported response choices at any time.',
  'Earning and redeeming reward stars': 'Stars are awarded after completed practice. Open Rewards to review the current balance, streaks, and available milestones.',
}

function FaqItem({ item, open, onToggle }) {
  return (
    <div className="border border-neutral-100 dark:border-neutral-800 rounded-2xl overflow-hidden bg-white dark:bg-neutral-900">
      <button onClick={onToggle} className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition">
        <span className="font-semibold text-sm text-neutral-800 dark:text-neutral-100">{item.q}</span>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown className="w-5 h-5 text-neutral-400 shrink-0" />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <p className="px-5 pb-4 text-sm text-neutral-500 dark:text-neutral-400 leading-relaxed">{item.a}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function HelpPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [openId, setOpenId] = useState(0)
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [contact, setContact] = useState({ name: '', email: '', subject: '', message: '' })
  const [sending, setSending] = useState(false)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return FAQS
    return FAQS.filter((f) => f.q.toLowerCase().includes(q) || f.a.toLowerCase().includes(q) || f.tag.toLowerCase().includes(q))
  }, [query])

  const openQuickAction = (action) => {
    if (action.path) {
      navigate(action.path)
      return
    }
    if (action.target === 'faq') {
      setQuery('first therapy session')
      setOpenId(0)
    }
    document.getElementById(action.target)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!contact.name || !contact.email || !contact.message) {
      toast.error('Please fill in name, email and message')
      return
    }
    setSending(true)
    try {
      await contactAPI.submitContact({
        name: contact.name,
        email: contact.email,
        subject: contact.subject || 'Support request',
        message: contact.message,
      })
      toast.success('Message sent! We\'ll reply within 24 hours')
      setContact({ name: '', email: '', subject: '', message: '' })
    } catch (err) {
      toast.error('Could not send message. Please try again.')
    } finally {
      setSending(false)
    }
  }

  return (
    <DashboardLayout title="Help & Support" subtitle="Find answers and reach our team" icon={HelpCircle}>
      {/* Search */}
      <Card className="p-6 mb-6 bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-primary-900/20 dark:to-secondary-900/20">
        <div className="text-center max-w-xl mx-auto">
          <div className="w-14 h-14 mx-auto bg-gradient-to-br from-primary-500 to-secondary-500 rounded-2xl flex items-center justify-center shadow-md mb-4">
            <LifeBuoy className="w-7 h-7 text-white" />
          </div>
          <h2 className="text-xl font-bold text-neutral-900 dark:text-white mb-1">How can we help you?</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-5">Search our knowledge base or browse the FAQs below</p>
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for help… e.g. 'Tamil word check'"
              className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 text-sm text-neutral-800 dark:text-white outline-none focus:ring-2 focus:ring-primary-200 shadow-sm"
            />
          </div>
        </div>
      </Card>

      {/* Quick actions */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {QUICK_ACTIONS.map((a, i) => (
          <motion.button
            key={a.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            whileHover={{ y: -4 }}
            onClick={() => openQuickAction(a)}
            className="text-left bg-white dark:bg-neutral-900 rounded-2xl p-5 border border-neutral-100 dark:border-neutral-800 shadow-md hover:shadow-lg transition"
          >
            <div className={`w-12 h-12 bg-gradient-to-br ${a.color} rounded-xl flex items-center justify-center mb-4 shadow-md`}>
              <a.icon className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-bold text-neutral-900 dark:text-white text-sm mb-1">{a.title}</h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">{a.desc}</p>
          </motion.button>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* FAQ */}
        <div id="faq" className="lg:col-span-2 scroll-mt-24">
          <SectionTitle title="Frequently Asked Questions" subtitle={`${filtered.length} result${filtered.length === 1 ? '' : 's'}`} icon={HelpCircle} />
          <div className="space-y-3">
            {filtered.length === 0 ? (
              <Card className="p-10 text-center">
                <p className="text-sm text-neutral-500 dark:text-neutral-400">No FAQs match "{query}". Try the contact form instead.</p>
              </Card>
            ) : (
              filtered.map((item, i) => (
                <FaqItem key={item.q} item={item} open={openId === i} onToggle={() => setOpenId(openId === i ? -1 : i)} />
              ))
            )}
          </div>
        </div>

        {/* Sidebar: contact + channels + articles */}
        <div className="space-y-6">
          <Card id="contact-support" className="p-6 scroll-mt-24">
            <SectionTitle title="Contact Support" icon={Send} />
            <form onSubmit={handleSubmit} className="space-y-3">
              <input
                value={contact.name}
                onChange={(e) => setContact({ ...contact, name: e.target.value })}
                placeholder="Your name"
                className="w-full px-4 py-2.5 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 outline-none focus:ring-2 focus:ring-primary-200 text-neutral-800 dark:text-white"
              />
              <input
                type="email"
                value={contact.email}
                onChange={(e) => setContact({ ...contact, email: e.target.value })}
                placeholder="Email address"
                className="w-full px-4 py-2.5 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 outline-none focus:ring-2 focus:ring-primary-200 text-neutral-800 dark:text-white"
              />
              <input
                value={contact.subject}
                onChange={(e) => setContact({ ...contact, subject: e.target.value })}
                placeholder="Subject"
                className="w-full px-4 py-2.5 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 outline-none focus:ring-2 focus:ring-primary-200 text-neutral-800 dark:text-white"
              />
              <textarea
                value={contact.message}
                onChange={(e) => setContact({ ...contact, message: e.target.value })}
                placeholder="How can we help?"
                rows={4}
                className="w-full px-4 py-2.5 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 outline-none focus:ring-2 focus:ring-primary-200 text-neutral-800 dark:text-white resize-none"
              />
              <GradientButton type="submit" disabled={sending} className="w-full"><Send className="w-4 h-4" /> {sending ? 'Sending…' : 'Send Message'}</GradientButton>
            </form>
          </Card>

          <Card className="p-6">
            <SectionTitle title="Support Channels" icon={MessageCircle} />
            <a href="mailto:speakeasy@amrita.edu" className="flex items-center gap-3 p-3 rounded-xl hover:bg-neutral-50 dark:hover:bg-neutral-800 transition">
              <div className="w-10 h-10 bg-primary-50 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
                <Mail className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Email Us</div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400">speakeasy@amrita.edu</div>
              </div>
            </a>
            <div className="flex items-center gap-3 p-3 rounded-xl">
              <div className="w-10 h-10 bg-accent-50 dark:bg-accent-900/30 rounded-xl flex items-center justify-center">
                <Clock className="w-5 h-5 text-accent-600 dark:text-accent-400" />
              </div>
              <div>
                <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Support Hours</div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400">Mon–Fri, 9:00 AM – 6:00 PM IST</div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <SectionTitle title="Popular Articles" icon={BookOpen} />
            <div className="space-y-1">
              {ARTICLES.map((a) => (
                <button
                  key={a}
                  onClick={() => setSelectedArticle(selectedArticle === a ? null : a)}
                  aria-expanded={selectedArticle === a}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl text-sm text-neutral-600 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition group"
                >
                  <span className="flex items-center gap-2.5 text-left"><FileText className="w-4 h-4 text-secondary-500 shrink-0" /> {a}</span>
                  <ArrowRight className="w-4 h-4 text-neutral-300 group-hover:translate-x-0.5 transition-transform shrink-0" />
                </button>
              ))}
            </div>
            <AnimatePresence mode="wait">
              {selectedArticle && (
                <motion.div
                  key={selectedArticle}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-4 rounded-xl bg-primary-50 dark:bg-primary-900/20 p-4 text-sm leading-relaxed text-neutral-700 dark:text-neutral-200"
                >
                  <strong className="block mb-1">{selectedArticle}</strong>
                  {ARTICLE_CONTENT[selectedArticle]}
                </motion.div>
              )}
            </AnimatePresence>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}

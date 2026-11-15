import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mail, ArrowLeft, Send, CheckCircle2, Brain, Shield, Star, Sparkles, RotateCcw } from 'lucide-react'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const floatingItems = [
  { emoji: '🔐', x: '12%', y: '18%', delay: 0, duration: 6 },
  { emoji: '✉️', x: '82%', y: '22%', delay: 1, duration: 7 },
  { emoji: '⭐', x: '18%', y: '74%', delay: 2, duration: 5 },
  { emoji: '✨', x: '78%', y: '78%', delay: 0.5, duration: 8 },
  { emoji: '🗝️', x: '50%', y: '12%', delay: 1.5, duration: 6 },
]

function SidePanel() {
  return (
    <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden items-center justify-center p-12 bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700">
      <div className="absolute inset-0 bg-grid opacity-10" />

      {floatingItems.map((item, i) => (
        <motion.div
          key={i}
          animate={{ y: [-15, 15, -15] }}
          transition={{ duration: item.duration, repeat: Infinity, ease: 'easeInOut', delay: item.delay }}
          className="absolute text-4xl select-none"
          style={{ left: item.x, top: item.y }}
        >
          {item.emoji}
        </motion.div>
      ))}

      <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 15, repeat: Infinity }}
        className="absolute top-16 left-8 w-64 h-64 bg-secondary-400/30 rounded-full blur-3xl" />
      <motion.div animate={{ scale: [1.2, 1, 1.2] }} transition={{ duration: 20, repeat: Infinity }}
        className="absolute bottom-16 right-8 w-80 h-80 bg-primary-300/30 rounded-full blur-3xl" />

      <div className="relative z-10 text-center max-w-md">
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
          <div className="w-20 h-20 mx-auto mb-8 bg-white/15 backdrop-blur rounded-3xl flex items-center justify-center border border-white/25 shadow-2xl">
            <span className="text-white font-bold text-3xl tracking-tight">SE</span>
          </div>
          <h2 className="text-4xl font-bold text-white mb-4">Forgot your password?</h2>
          <p className="text-lg text-white/70">
            No worries — it happens. We'll help you get back to giving every child's voice a chance to be heard.
          </p>

          <div className="flex justify-center gap-6 mt-10">
            {[
              { icon: Brain, label: 'AI-Powered' },
              { icon: Shield, label: 'Privacy-First' },
              { icon: Star, label: 'Gamified' },
            ].map((item, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 + i * 0.15 }}
                className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 bg-white/10 backdrop-blur rounded-xl flex items-center justify-center border border-white/20">
                  <item.icon className="w-5 h-5 text-white" />
                </div>
                <span className="text-xs text-white/60 font-medium">{item.label}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const sendCode = async (e) => {
    e?.preventDefault()
    if (!EMAIL_REGEX.test(email.trim())) {
      setError('Please enter a valid email address')
      toast.error('That email doesn\'t look right')
      return
    }
    setError('')
    setLoading(true)
    try {
      await authAPI.forgotPassword(email.trim())
      setLoading(false)
      setSent(true)
      toast.success('If that account exists, a reset code has been sent.')
    } catch (requestError) {
      setLoading(false)
      toast.error(requestError.response?.data?.detail || 'Could not request a reset code. Please try again.')
    }
  }

  const resend = async () => {
    setLoading(true)
    try {
      await authAPI.forgotPassword(email.trim())
      setLoading(false)
      toast.success('If that account exists, a new code has been sent.')
    } catch (requestError) {
      setLoading(false)
      toast.error(requestError.response?.data?.detail || 'Could not resend the code. Please try again.')
    }
  }

  return (
    <div className="min-h-screen flex bg-neutral-50 dark:bg-neutral-950">
      <SidePanel />

      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 relative">
        <div className="absolute inset-0 bg-gradient-mesh opacity-30 dark:opacity-10" />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md relative z-10"
        >
          <button
            onClick={() => navigate('/login')}
            className="inline-flex items-center text-neutral-500 dark:text-neutral-400 hover:text-primary-600 dark:hover:text-primary-400 mb-8 transition text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Login
          </button>

          <div className="bg-white dark:bg-neutral-900 rounded-3xl shadow-premium border border-neutral-200/70 dark:border-neutral-800 p-8 sm:p-10">
            <AnimatePresence mode="wait">
              {!sent ? (
                <motion.div
                  key="form"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.35 }}
                >
                  <div className="flex items-center gap-3 mb-8">
                    <div className="w-12 h-12 bg-gradient-to-br from-primary-600 to-secondary-500 rounded-2xl flex items-center justify-center shadow-lg">
                      <Sparkles className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">Reset Password</h1>
                      <p className="text-sm text-neutral-500 dark:text-neutral-400">We'll email you a reset code</p>
                    </div>
                  </div>

                  <form onSubmit={sendCode} className="space-y-5">
                    <div>
                      <label htmlFor="password-reset-email" className="block text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">Email Address</label>
                      <div className="relative">
                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                        <input
                          type="email"
                          id="password-reset-email"
                          value={email}
                          onChange={(e) => { setEmail(e.target.value); if (error) setError('') }}
                          placeholder="your@email.com"
                          className="w-full pl-12 pr-4 py-4 border-2 border-neutral-200 dark:border-neutral-700 dark:bg-neutral-800 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all text-neutral-800 dark:text-white"
                        />
                      </div>
                      {error && <p className="text-coral-500 text-sm mt-1.5">{error}</p>}
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      className="btn-primary w-full !py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <span className="flex items-center justify-center gap-2">
                          <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                            className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full inline-block" />
                          Sending...
                        </span>
                      ) : (
                        <span className="flex items-center justify-center gap-2">
                          <Send className="w-5 h-5" />
                          Send Reset Code
                        </span>
                      )}
                    </button>
                  </form>
                </motion.div>
              ) : (
                <motion.div
                  key="sent"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.35 }}
                  className="text-center"
                >
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 200, damping: 14 }}
                    className="w-20 h-20 mx-auto mb-6 bg-accent-100 dark:bg-accent-900/30 rounded-full flex items-center justify-center"
                  >
                    <CheckCircle2 className="w-11 h-11 text-accent-600 dark:text-accent-400" />
                  </motion.div>

                  <h1 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">Check your inbox</h1>
                  <p className="text-neutral-500 dark:text-neutral-400 mb-1">We sent a password reset code to</p>
                  <p className="text-primary-600 dark:text-primary-400 font-semibold break-all mb-8">{email.trim()}</p>

                  <button
                    onClick={() => navigate('/verify-otp', { state: { email: email.trim() } })}
                    className="btn-primary w-full !py-4 text-lg mb-4"
                  >
                    Enter Reset Code
                  </button>

                  <p className="text-sm text-neutral-500 dark:text-neutral-400">
                    Didn't get it?{' '}
                    <button
                      onClick={resend}
                      disabled={loading}
                      className="inline-flex items-center gap-1 text-primary-600 dark:text-primary-400 hover:text-primary-700 font-semibold disabled:opacity-50"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Resend
                    </button>
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <p className="text-center text-xs text-neutral-400 dark:text-neutral-600 mt-8">
            Remembered it?{' '}
            <button onClick={() => navigate('/login')} className="text-primary-600 dark:text-primary-400 hover:text-primary-700 font-medium">
              Back to Login
            </button>
          </p>
        </motion.div>
      </div>
    </div>
  )
}

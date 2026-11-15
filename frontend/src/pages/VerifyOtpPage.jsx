import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, Brain, KeyRound, Shield, ShieldCheck, Star } from 'lucide-react'
import toast from 'react-hot-toast'
import { useLocation, useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'

const RESEND_SECONDS = 30

function maskEmail(email) {
  const [name, domain] = email.split('@')
  if (!domain) return email
  return `${name.slice(0, 1)}${'•'.repeat(Math.max(name.length - 1, 3))}@${domain}`
}

function SidePanel() {
  return (
    <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden items-center justify-center p-12 bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700">
      <div className="absolute inset-0 bg-grid opacity-10" />
      <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 15, repeat: Infinity }} className="absolute top-16 left-8 w-64 h-64 bg-secondary-400/30 rounded-full blur-3xl" />
      <motion.div animate={{ scale: [1.2, 1, 1.2] }} transition={{ duration: 20, repeat: Infinity }} className="absolute bottom-16 right-8 w-80 h-80 bg-primary-300/30 rounded-full blur-3xl" />

      <div className="relative z-10 text-center max-w-md">
        <div className="w-20 h-20 mx-auto mb-8 bg-white/15 backdrop-blur rounded-3xl flex items-center justify-center border border-white/25 shadow-2xl">
          <span className="text-white font-bold text-3xl tracking-tight">SE</span>
        </div>
        <h2 className="text-4xl font-bold text-white mb-4">Secure your account</h2>
        <p className="text-lg text-white/70">Verify the one-time code, then choose a strong new password.</p>
        <div className="flex justify-center gap-6 mt-10">
          {[
            { icon: Brain, label: 'AI-Powered' },
            { icon: Shield, label: 'Privacy-First' },
            { icon: Star, label: 'Child-Friendly' },
          ].map((item) => (
            <div key={item.label} className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 bg-white/10 backdrop-blur rounded-xl flex items-center justify-center border border-white/20">
                <item.icon className="w-5 h-5 text-white" />
              </div>
              <span className="text-xs text-white/60 font-medium">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function VerifyOtpPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const email = location.state?.email || ''
  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const [stage, setStage] = useState('otp')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [countdown, setCountdown] = useState(RESEND_SECONDS)
  const inputsRef = useRef([])

  useEffect(() => {
    inputsRef.current[0]?.focus()
  }, [])

  useEffect(() => {
    if (countdown <= 0 || stage !== 'otp') return undefined
    const timer = window.setInterval(() => {
      setCountdown((previous) => (previous <= 1 ? 0 : previous - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [countdown, stage])

  const updateDigit = (index, value) => {
    const digit = value.replace(/\D/g, '').slice(-1)
    setDigits((previous) => previous.map((item, itemIndex) => (itemIndex === index ? digit : item)))
    if (digit && index < 5) inputsRef.current[index + 1]?.focus()
  }

  const handleKeyDown = (index, event) => {
    if (event.key === 'Backspace' && !digits[index] && index > 0) {
      setDigits((previous) => previous.map((item, itemIndex) => (itemIndex === index - 1 ? '' : item)))
      inputsRef.current[index - 1]?.focus()
    }
  }

  const handlePaste = (event) => {
    event.preventDefault()
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (!pasted) return
    setDigits(Array.from({ length: 6 }, (_, index) => pasted[index] || ''))
    inputsRef.current[Math.min(pasted.length, 5)]?.focus()
  }

  const verifyCode = async () => {
    const otp = digits.join('')
    if (!email) {
      toast.error('Please request a new reset code first')
      navigate('/forgot-password')
      return
    }
    if (otp.length !== 6) {
      toast.error('Please enter all 6 digits')
      return
    }

    setBusy(true)
    try {
      await authAPI.verifyOtp(email, otp)
      setStage('reset')
      toast.success('Code verified. Choose a new password.')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'That code could not be verified. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const resendCode = async () => {
    if (countdown > 0 || busy) return
    if (!email) {
      navigate('/forgot-password')
      return
    }

    setBusy(true)
    try {
      await authAPI.forgotPassword(email)
      setDigits(['', '', '', '', '', ''])
      setCountdown(RESEND_SECONDS)
      inputsRef.current[0]?.focus()
      toast.success('If that account exists, a new code has been sent.')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not resend the code. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const submitNewPassword = async (event) => {
    event.preventDefault()
    if (newPassword.length < 10) {
      toast.error('Password must be at least 10 characters')
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }

    setBusy(true)
    try {
      await authAPI.resetPassword({ email, otp: digits.join(''), new_password: newPassword })
      toast.success('Password reset successfully. You can now sign in.')
      navigate('/login')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not reset the password. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-neutral-50 dark:bg-neutral-950">
      <SidePanel />
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 relative">
        <div className="absolute inset-0 bg-gradient-mesh opacity-30 dark:opacity-10" />
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md relative z-10">
          <button onClick={() => navigate(stage === 'otp' ? '/forgot-password' : '/verify-otp', { state: { email } })} className="inline-flex items-center text-neutral-500 dark:text-neutral-400 hover:text-primary-600 mb-8 text-sm font-medium">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </button>

          <div className="bg-white dark:bg-neutral-900 rounded-3xl shadow-premium border border-neutral-200/70 dark:border-neutral-800 p-8 sm:p-10">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-600 to-secondary-500 rounded-2xl flex items-center justify-center shadow-lg">
                <KeyRound className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">{stage === 'otp' ? 'Verify Code' : 'Choose New Password'}</h1>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">{stage === 'otp' ? 'Enter the 6-digit code' : 'Use at least 10 characters'}</p>
              </div>
            </div>

            <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-8">
              {email ? <>Code sent to <span className="font-semibold text-neutral-700 dark:text-neutral-200">{maskEmail(email)}</span></> : 'No reset email was provided. Go back and request a new code.'}
            </p>

            {stage === 'otp' ? (
              <>
                <div className="flex justify-between gap-2 sm:gap-3 mb-8" onPaste={handlePaste}>
                  {digits.map((digit, index) => (
                    <input
                      key={index}
                      ref={(element) => { inputsRef.current[index] = element }}
                      aria-label={`Code digit ${index + 1}`}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(event) => updateDigit(index, event.target.value)}
                      onKeyDown={(event) => handleKeyDown(index, event)}
                      onFocus={(event) => event.target.select()}
                      className={`w-12 h-14 sm:w-14 sm:h-16 text-center text-2xl font-bold rounded-2xl border-2 outline-none transition-all text-neutral-900 dark:text-white bg-neutral-50 dark:bg-neutral-800 ${digit ? 'border-primary-500 ring-2 ring-primary-500/20' : 'border-neutral-200 dark:border-neutral-700'} focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30`}
                    />
                  ))}
                </div>
                <button onClick={verifyCode} disabled={busy || !email} className="btn-primary w-full !py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed">
                  <span className="flex items-center justify-center gap-2"><ShieldCheck className="w-5 h-5" />{busy ? 'Verifying...' : 'Verify Code'}</span>
                </button>
                <div className="mt-6 text-center text-sm">
                  {countdown > 0 ? (
                    <p className="text-neutral-500 dark:text-neutral-400">Resend code in <span className="font-semibold text-primary-600 dark:text-primary-400">{countdown}s</span></p>
                  ) : (
                    <button onClick={resendCode} disabled={busy} className="text-primary-600 dark:text-primary-400 hover:text-primary-700 font-semibold disabled:opacity-50">Resend code</button>
                  )}
                </div>
              </>
            ) : (
              <form onSubmit={submitNewPassword} className="space-y-5">
                <div>
                  <label htmlFor="new-password" className="block text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">New Password</label>
                  <input id="new-password" type="password" autoComplete="new-password" minLength={10} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} className="w-full px-4 py-4 border-2 border-neutral-200 dark:border-neutral-700 dark:bg-neutral-800 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-neutral-800 dark:text-white" />
                </div>
                <div>
                  <label htmlFor="confirm-new-password" className="block text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">Confirm New Password</label>
                  <input id="confirm-new-password" type="password" autoComplete="new-password" minLength={10} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="w-full px-4 py-4 border-2 border-neutral-200 dark:border-neutral-700 dark:bg-neutral-800 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-neutral-800 dark:text-white" />
                </div>
                <button type="submit" disabled={busy} className="btn-primary w-full !py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed">{busy ? 'Resetting...' : 'Reset Password'}</button>
              </form>
            )}
          </div>

          <p className="text-center text-xs text-neutral-400 dark:text-neutral-600 mt-8">
            Wrong email? <button onClick={() => navigate('/forgot-password')} className="text-primary-600 dark:text-primary-400 hover:text-primary-700 font-medium">Request another code</button>
          </p>
        </motion.div>
      </div>
    </div>
  )
}

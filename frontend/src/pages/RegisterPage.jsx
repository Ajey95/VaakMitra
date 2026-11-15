import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { User, Mail, Lock, ArrowLeft, ArrowRight, Eye, EyeOff, CheckCircle, Star, Sparkles, BookOpen, Heart } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import { Link, useNavigate } from 'react-router-dom'

import cloudAnimationImg from '../assets/images/cloud_animation.png'
import chefKidImg from '../assets/images/chef_kid.png'

const registerSchema = z.object({
  full_name: z.string().trim().min(2, 'Name must be at least 2 characters').max(100, 'Name must be at most 100 characters'),
  child_name: z.string().trim().min(2, 'Child name must be at least 2 characters').max(100, 'Child name must be at most 100 characters'),
  child_age: z.coerce.number().min(4, 'Age must be at least 4').max(12, 'Age must be at most 12'),
  email: z.string().trim().toLowerCase().email('Please enter a valid email address'),
  password: z.string()
    .min(10, 'Password must be at least 10 characters')
    .max(72, 'Password must be at most 72 characters')
    .regex(/[A-Z]/, 'Password needs an uppercase letter')
    .regex(/[a-z]/, 'Password needs a lowercase letter')
    .regex(/[0-9]/, 'Password needs a number')
    .regex(/[^A-Za-z0-9]/, 'Password needs a special character'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
  language: z.enum(['Tamil', 'Telugu', 'English']).default('Tamil')
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
})

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [step, setStep] = useState(1)
  const [isChecking, setIsChecking] = useState(true)
  const { isAuthenticated, user, authReady, setAuth } = useAuthStore()
  const navigate = useNavigate()
  
  useEffect(() => {
    const timer = setTimeout(() => {
      if (authReady && isAuthenticated && user) {
        if (user.role === 'admin') navigate('/admin', { replace: true })
        else navigate('/dashboard', { replace: true })
      } else {
        setIsChecking(false)
      }
    }, 50)
    return () => clearTimeout(timer)
  }, [authReady, isAuthenticated, user, navigate])
  
  const { register, handleSubmit, formState: { errors, isSubmitting }, trigger, watch } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: { language: 'Tamil' }
  })
  
  // Don't render while checking auth
  if (isChecking) {
    return <div className="min-h-screen bg-white" />
  }
  
  const password = watch('password', '')
  const getPasswordStrength = () => {
    if (!password) return { level: 0, label: '', color: '' }
    let score = 0
    if (password.length >= 10) score++
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++
    if (/[0-9]/.test(password)) score++
    if (/[^A-Za-z0-9]/.test(password)) score++
    if (score <= 1) return { level: 1, label: 'Weak', color: 'bg-red-500' }
    if (score === 2) return { level: 2, label: 'Fair', color: 'bg-amber-500' }
    if (score === 3) return { level: 3, label: 'Strong', color: 'bg-emerald-500' }
    return { level: 4, label: 'Very Strong', color: 'bg-green-600' }
  }
  const passwordStrength = getPasswordStrength()
  
  const goToStep2 = async () => {
    const isValid = await trigger(['full_name', 'child_name', 'child_age', 'language'])
    if (isValid) setStep(2)
  }
  
  const onSubmit = async (data) => {
    try {
      const registerData = {
        full_name: data.full_name,
        child_name: data.child_name,
        child_age: data.child_age,
        email: data.email,
        password: data.password,
        confirm_password: data.confirmPassword,
        language: data.language
      }
      const response = await authAPI.register(registerData)
      setAuth(response.data.user, response.data.access_token)
      toast.success('Account created! Welcome to SpeakEasy.')
      navigate('/dashboard', { replace: true })
    } catch (error) {
      if (!error.response) {
        toast.error('Cannot reach the server. Please check that the backend is running.')
        return
      }
      if (error.response.status === 503) {
        toast.error(error.response.data?.detail || 'Registration is temporarily unavailable. Please try again in a moment.')
        return
      }
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (Array.isArray(detail)) detail.forEach(err => toast.error(`${err.loc[1]}: ${err.msg}`))
        else if (typeof detail === 'string') toast.error(detail)
        else toast.error('Registration failed')
      } else toast.error('Registration failed. Please try again.')
    }
  }
  
  const floatingItems = [
    { emoji: 'அ', x: '8%', y: '12%', delay: 0, duration: 7 },
    { emoji: 'ஆ', x: '88%', y: '18%', delay: 1.5, duration: 6 },
    { emoji: '⭐', x: '12%', y: '78%', delay: 0.8, duration: 8 },
    { emoji: '🎉', x: '82%', y: '82%', delay: 2, duration: 5 },
    { emoji: '🗣️', x: '45%', y: '8%', delay: 0.5, duration: 7 },
  ]
  
  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Illustration */}
      <div className="hidden lg:flex lg:w-5/12 bg-gradient-to-br from-purple-900 via-violet-800 to-fuchsia-900 relative overflow-hidden items-center justify-center p-12">
        <div className="absolute inset-0 bg-grid opacity-10" />
        
        {floatingItems.map((item, i) => (
          <motion.div key={i} animate={{ y: [-15, 15, -15] }}
            transition={{ duration: item.duration, repeat: Infinity, ease: 'easeInOut', delay: item.delay }}
            className="absolute text-4xl tamil-letter font-bold text-white/20"
            style={{ left: item.x, top: item.y }}>
            {item.emoji}
          </motion.div>
        ))}
        
        <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 18, repeat: Infinity }}
          className="absolute top-20 left-10 w-64 h-64 bg-pink-500/15 rounded-full blur-3xl" />
        <motion.div animate={{ scale: [1.2, 1, 1.2] }} transition={{ duration: 22, repeat: Infinity }}
          className="absolute bottom-20 right-10 w-80 h-80 bg-purple-400/15 rounded-full blur-3xl" />
        
        <div className="relative z-10 text-center">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            <div className="grid grid-cols-2 gap-4 mb-10 max-w-sm mx-auto">
              <motion.img whileHover={{ scale: 1.05, rotate: -3 }} src={cloudAnimationImg} alt="Happy Learning"
                className="rounded-2xl shadow-2xl h-44 w-full object-cover border border-white/10" />
              <motion.img whileHover={{ scale: 1.05, rotate: 3 }} src={chefKidImg} alt="Fun Activities"
                className="rounded-2xl shadow-2xl h-44 w-full object-cover border border-white/10" />
            </div>
            
            <h2 className="text-3xl font-bold text-white mb-3">Join the SpeakEasy Family</h2>
            <p className="text-white/60 max-w-sm mx-auto mb-8">Begin your child's speech therapy journey with AI-powered, gamified learning designed by experts.</p>
            
            <div className="space-y-3 text-left max-w-sm mx-auto">
              {[
                { icon: CheckCircle, text: '6 progressive Tamil lessons' },
                { icon: CheckCircle, text: 'Real-time AI speech evaluation' },
                { icon: CheckCircle, text: '3D interactive candle blow test' },
                { icon: CheckCircle, text: 'Star rewards & progress tracking' },
              ].map((item, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + i * 0.1 }}
                  className="flex items-center gap-3 text-white/80 text-sm">
                  <item.icon className="w-5 h-5 text-green-400 flex-shrink-0" />
                  {item.text}
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
      
      {/* Right Panel — Form */}
      <div className="w-full lg:w-7/12 flex items-center justify-center p-6 bg-white relative overflow-y-auto">
        <div className="absolute inset-0 bg-gradient-mesh opacity-20" />
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-lg relative z-10 py-8"
        >
          <Link to="/" className="inline-flex items-center text-neutral-500 hover:text-primary-600 mb-8 transition text-sm font-medium">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Link>
          
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-pink-500 rounded-2xl flex items-center justify-center shadow-lg">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Create Account</h1>
                <p className="text-sm text-neutral-500">Step {step} of 2 — {step === 1 ? 'Child Details' : 'Account Setup'}</p>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="flex gap-2 mt-4">
              <div className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${step >= 1 ? 'bg-gradient-to-r from-purple-500 to-pink-500' : 'bg-neutral-200'}`} />
              <div className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${step >= 2 ? 'bg-gradient-to-r from-pink-500 to-rose-500' : 'bg-neutral-200'}`} />
            </div>
          </div>
          
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <AnimatePresence mode="wait">
              {step === 1 && (
                <motion.div key="step1" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="space-y-5">
                  <div>
                    <label htmlFor="register-full-name" className="block text-sm font-semibold text-neutral-700 mb-2">Parent / Guardian Name</label>
                    <div className="relative">
                      <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                      <input {...register('full_name')} id="register-full-name" type="text" autoComplete="name" maxLength={100}
                        className="w-full pl-12 pr-4 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all"
                        placeholder="Your full name" />
                    </div>
                    {errors.full_name && <p className="text-coral-500 text-sm mt-1.5">{errors.full_name.message}</p>}
                  </div>
                  
                  <div>
                    <label htmlFor="register-child-name" className="block text-sm font-semibold text-neutral-700 mb-2">Child's Name</label>
                    <div className="relative">
                      <Heart className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                      <input {...register('child_name')} id="register-child-name" type="text" autoComplete="off" maxLength={100}
                        className="w-full pl-12 pr-4 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all"
                        placeholder="Your child's name" />
                    </div>
                    {errors.child_name && <p className="text-coral-500 text-sm mt-1.5">{errors.child_name.message}</p>}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="register-child-age" className="block text-sm font-semibold text-neutral-700 mb-2">Child's Age</label>
                      <input {...register('child_age')} id="register-child-age" type="number" min="4" max="12"
                        className="w-full px-4 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all"
                        placeholder="4-12" />
                      {errors.child_age && <p className="text-coral-500 text-sm mt-1.5">{errors.child_age.message}</p>}
                    </div>
                    <div>
                      <label htmlFor="register-language" className="block text-sm font-semibold text-neutral-700 mb-2">Language</label>
                      <select {...register('language')} id="register-language"
                        className="w-full px-4 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all appearance-none bg-white">
                        <option value="Tamil">Tamil</option>
                        <option value="Telugu">Telugu</option>
                        <option value="English">English</option>
                      </select>
                    </div>
                  </div>
                  
                  <button type="button" onClick={goToStep2}
                    className="w-full py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-2xl font-semibold text-lg shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2">
                    Continue
                    <ArrowRight className="w-5 h-5" />
                  </button>
                </motion.div>
              )}
              
              {step === 2 && (
                <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-5">
                  <div>
                    <label htmlFor="register-email" className="block text-sm font-semibold text-neutral-700 mb-2">Email Address</label>
                    <div className="relative">
                      <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                      <input {...register('email')} id="register-email" type="email" autoComplete="email"
                        className="w-full pl-12 pr-4 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all"
                        placeholder="your@email.com" />
                    </div>
                    {errors.email && <p className="text-coral-500 text-sm mt-1.5">{errors.email.message}</p>}
                  </div>
                  
                  <div>
                    <label htmlFor="register-password" className="block text-sm font-semibold text-neutral-700 mb-2">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                      <input {...register('password')} id="register-password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" maxLength={72}
                        className="w-full pl-12 pr-12 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all"
                        placeholder="Minimum 10 characters" />
                      <button type="button" onClick={() => setShowPassword(!showPassword)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition">
                        {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                      </button>
                    </div>
                    {/* Strength bar */}
                    {password && (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="flex gap-1 flex-1">
                          {[1, 2, 3, 4].map((level) => (
                            <div key={level} className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${level <= passwordStrength.level ? passwordStrength.color : 'bg-neutral-200'}`} />
                          ))}
                        </div>
                        <span className="text-xs text-neutral-500 font-medium">{passwordStrength.label}</span>
                      </div>
                    )}
                    {errors.password && <p className="text-coral-500 text-sm mt-1.5">{errors.password.message}</p>}
                  </div>
                  
                  <div>
                    <label htmlFor="register-confirm-password" className="block text-sm font-semibold text-neutral-700 mb-2">Confirm Password</label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                      <input {...register('confirmPassword')} id="register-confirm-password" type={showConfirmPassword ? 'text' : 'password'} autoComplete="new-password" maxLength={72}
                        className="w-full pl-12 pr-12 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all"
                        placeholder="Re-enter your password" />
                      <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        aria-label={showConfirmPassword ? 'Hide confirmed password' : 'Show confirmed password'}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition">
                        {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                      </button>
                    </div>
                    {errors.confirmPassword && <p className="text-coral-500 text-sm mt-1.5">{errors.confirmPassword.message}</p>}
                  </div>
                  
                  <div className="flex items-start gap-3">
                    <input id="register-terms" type="checkbox" required className="w-4 h-4 mt-1 text-purple-600 border-neutral-300 rounded focus:ring-purple-500" />
                    <label htmlFor="register-terms" className="text-sm text-neutral-600">
                      I agree to the <Link to="/about#terms" className="text-purple-600 hover:text-purple-700 font-medium">Terms of Service</Link> and <Link to="/about#privacy" className="text-purple-600 hover:text-purple-700 font-medium">Privacy Policy</Link>
                    </label>
                  </div>
                  
                  <div className="flex gap-3">
                    <button type="button" onClick={() => setStep(1)}
                      className="px-6 py-4 border-2 border-neutral-200 text-neutral-700 rounded-2xl font-semibold hover:bg-neutral-50 transition-all">
                      <ArrowLeft className="w-5 h-5" />
                    </button>
                    <button type="submit" disabled={isSubmitting}
                      className="flex-1 py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-2xl font-semibold text-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed">
                      {isSubmitting ? (
                        <span className="flex items-center justify-center gap-2">
                          <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                            className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full inline-block" />
                          Creating account...
                        </span>
                      ) : 'Create Account'}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </form>
          
          <div className="mt-8 text-center">
            <p className="text-neutral-600">
              Already have an account?{' '}
              <Link to="/login" className="text-purple-600 hover:text-purple-700 font-semibold">Sign in</Link>
            </p>
          </div>
          
          <p className="text-center text-xs text-neutral-400 mt-6">
            Your data is encrypted and protected. We never share your information with third parties.
          </p>
        </motion.div>
      </div>
    </div>
  )
}

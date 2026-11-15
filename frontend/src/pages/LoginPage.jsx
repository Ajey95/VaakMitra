import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Mail, Lock, ArrowLeft, Eye, EyeOff, Sparkles, Star, Brain, Shield } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import { Link, useNavigate } from 'react-router-dom'

import happyBearImg from '../assets/images/happy_bear.png'
import strawberryImg from '../assets/images/strawberry_cartoon.png'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [isChecking, setIsChecking] = useState(true)
  const [isDemoSubmitting, setIsDemoSubmitting] = useState(false)
  const { isAuthenticated, user, authReady } = useAuthStore()
  const setAuth = useAuthStore((state) => state.setAuth)
  const navigate = useNavigate()
  
  useEffect(() => {
    // The HttpOnly session cookie is restored by App before this route renders.
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
  
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(loginSchema)
  })
  
  // Don't render anything while checking auth to prevent blink
  if (isChecking) {
    return <div className="min-h-screen bg-white" />
  }
  
  const loginWithCredentials = async (data) => {
    try {
      const response = await authAPI.login(data)
      setAuth(response.data.user, response.data.access_token)
      toast.success(`Welcome back, ${response.data.user.full_name}!`)
      setTimeout(() => {
        if (response.data.user.role === 'admin') navigate('/admin', { replace: true })
        else navigate('/dashboard', { replace: true })
      }, 100)
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed. Please check your credentials.')
    }
  }

  const onSubmit = (data) => loginWithCredentials(data)

  const enterDemo = async () => {
    setIsDemoSubmitting(true)
    try {
      await loginWithCredentials({ email: 'demo@speakeasy.app', password: 'Demo@1234' })
    } finally {
      setIsDemoSubmitting(false)
    }
  }
  
  const floatingItems = [
    { emoji: '🗣️', x: '10%', y: '15%', delay: 0, duration: 6 },
    { emoji: '⭐', x: '85%', y: '20%', delay: 1, duration: 7 },
    { emoji: '🎤', x: '15%', y: '75%', delay: 2, duration: 5 },
    { emoji: '📖', x: '80%', y: '80%', delay: 0.5, duration: 8 },
    { emoji: '✨', x: '50%', y: '10%', delay: 1.5, duration: 6 },
  ]
  
  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Illustration */}
      <div className="hidden lg:flex lg:w-1/2 bg-hero relative overflow-hidden items-center justify-center p-12">
        <div className="absolute inset-0 bg-grid opacity-10" />
        
        {/* Floating emojis */}
        {floatingItems.map((item, i) => (
          <motion.div
            key={i}
            animate={{ y: [-15, 15, -15] }}
            transition={{ duration: item.duration, repeat: Infinity, ease: 'easeInOut', delay: item.delay }}
            className="absolute text-4xl"
            style={{ left: item.x, top: item.y }}
          >
            {item.emoji}
          </motion.div>
        ))}
        
        {/* Gradient orbs */}
        <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 15, repeat: Infinity }}
          className="absolute top-20 left-10 w-64 h-64 bg-secondary-500/20 rounded-full blur-3xl" />
        <motion.div animate={{ scale: [1.2, 1, 1.2] }} transition={{ duration: 20, repeat: Infinity }}
          className="absolute bottom-20 right-10 w-80 h-80 bg-primary-400/20 rounded-full blur-3xl" />
        
        <div className="relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="grid grid-cols-2 gap-4 mb-10 max-w-md mx-auto">
              <motion.img whileHover={{ scale: 1.05, rotate: -3 }} src={happyBearImg} alt="Learning" className="rounded-2xl shadow-2xl h-48 w-full object-cover border border-white/10" />
              <motion.img whileHover={{ scale: 1.05, rotate: 3 }} src={strawberryImg} alt="Fun" className="rounded-2xl shadow-2xl h-48 w-full object-cover border border-white/10" />
            </div>
            <h2 className="text-4xl font-bold text-white mb-4">Welcome to SpeakEasy</h2>
            <p className="text-lg text-white/70 max-w-md">AI-powered speech therapy that makes every child's voice heard. Privacy-first, evidence-based, and beautifully gamified.</p>
            
            <div className="flex justify-center gap-6 mt-8">
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
      
      {/* Right Panel — Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 bg-white relative">
        <div className="absolute inset-0 bg-gradient-mesh opacity-30" />
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md relative z-10"
        >
          <Link to="/" className="inline-flex items-center text-neutral-500 hover:text-primary-600 mb-8 transition text-sm font-medium">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Link>
          
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-600 to-secondary-500 rounded-2xl flex items-center justify-center shadow-lg">
                <span className="text-white font-bold text-xl">SE</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Welcome Back!</h1>
                <p className="text-sm text-neutral-500">Sign in to continue your therapy journey</p>
              </div>
            </div>
          </div>
          
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                <input {...register('email')} type="email"
                  className="w-full pl-12 pr-4 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all text-neutral-800"
                  placeholder="your@email.com" />
              </div>
              {errors.email && <p className="text-coral-500 text-sm mt-1.5">{errors.email.message}</p>}
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-neutral-700 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                <input {...register('password')} type={showPassword ? 'text' : 'password'}
                  className="w-full pl-12 pr-12 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all text-neutral-800"
                  placeholder="••••••••" />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition">
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {errors.password && <p className="text-coral-500 text-sm mt-1.5">{errors.password.message}</p>}
            </div>
            
            <div className="flex items-center justify-between">
              <label className="flex items-center cursor-pointer">
                <input type="checkbox" className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500" />
                <span className="ml-2 text-sm text-neutral-600">Remember me</span>
              </label>
              <Link to="/forgot-password" className="text-sm text-primary-600 hover:text-primary-700 font-medium">Forgot password?</Link>
            </div>
            
            <button type="submit" disabled={isSubmitting}
              className="btn-primary w-full !py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed">
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full inline-block" />
                  Signing in...
                </span>
              ) : 'Sign In'}
            </button>

            <div className="rounded-2xl border-2 border-primary-100 bg-primary-50/70 p-4">
              <div className="mb-3 flex items-start gap-3">
                <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-primary-600 shadow-sm">
                  <Sparkles className="h-5 w-5" aria-hidden="true" />
                </span>
                <div>
                  <p className="font-bold text-neutral-800">Try the complete demo</p>
                  <p className="text-sm text-neutral-500">demo@speakeasy.app · Demo@1234</p>
                </div>
              </div>
              <button
                type="button"
                onClick={enterDemo}
                disabled={isDemoSubmitting || isSubmitting}
                className="w-full rounded-xl border border-primary-200 bg-white px-4 py-3 font-bold text-primary-700 shadow-sm transition hover:border-primary-400 hover:bg-primary-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isDemoSubmitting ? 'Opening Demo...' : 'Enter Demo'}
              </button>
            </div>
          </form>
          
          <div className="mt-8 text-center">
            <p className="text-neutral-600">
              Don't have an account?{' '}
              <Link to="/register" className="text-primary-600 hover:text-primary-700 font-semibold">Create one free</Link>
            </p>
          </div>
          
          <div className="mt-6 pt-6 border-t border-neutral-200">
            <Link to="/admin-login" className="block text-center text-sm text-neutral-400 hover:text-neutral-600 transition">
              Admin Login →
            </Link>
          </div>
          
          <p className="text-center text-xs text-neutral-400 mt-8">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </motion.div>
      </div>
    </div>
  )
}

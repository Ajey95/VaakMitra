import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Mail, Lock, ArrowLeft, Eye, EyeOff, Shield, AlertTriangle } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import { Link, useNavigate } from 'react-router-dom'

const adminLoginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

// Matrix-style falling characters
function MatrixRain() {
  const columns = Array.from({ length: 30 }, (_, i) => ({
    id: i,
    x: (i / 30) * 100,
    chars: 'அஆலதஅம்மாஅப்பா01SE',
    delay: Math.random() * 5,
    duration: Math.random() * 8 + 6,
    opacity: Math.random() * 0.15 + 0.05,
    size: Math.random() * 8 + 10,
  }))
  
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {columns.map((col) => (
        <motion.div
          key={col.id}
          animate={{ y: ['-100%', '100%'] }}
          transition={{ duration: col.duration, repeat: Infinity, ease: 'linear', delay: col.delay }}
          className="absolute font-mono text-green-500/20 whitespace-nowrap"
          style={{ left: `${col.x}%`, fontSize: col.size, opacity: col.opacity, writingMode: 'vertical-rl' }}
        >
          {col.chars}
        </motion.div>
      ))}
    </div>
  )
}

export default function AdminLoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [isChecking, setIsChecking] = useState(true)
  const { isAuthenticated, user, authReady } = useAuthStore()
  const setAuth = useAuthStore((state) => state.setAuth)
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
  
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(adminLoginSchema)
  })
  
  // Don't render while checking auth
  if (isChecking) {
    return <div className="min-h-screen bg-neutral-950" />
  }
  
  const onSubmit = async (data) => {
    try {
      const response = await authAPI.login(data)
      if (response.data.user.role !== 'admin') {
        toast.error('Access denied: Admin privileges required')
        return
      }
      setAuth(response.data.user, response.data.access_token)
      toast.success('Welcome Admin!')
      setTimeout(() => navigate('/admin', { replace: true }), 100)
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Admin login failed')
    }
  }
  
  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-4 relative overflow-hidden">
      <MatrixRain />
      
      {/* Gradient orbs */}
      <div className="absolute inset-0 pointer-events-none">
        <motion.div animate={{ scale: [1, 1.4, 1], rotate: [0, 180, 360] }} transition={{ duration: 30, repeat: Infinity }}
          className="absolute top-20 left-10 w-72 h-72 bg-red-900/20 rounded-full blur-3xl" />
        <motion.div animate={{ scale: [1.3, 1, 1.3] }} transition={{ duration: 25, repeat: Infinity }}
          className="absolute bottom-20 right-10 w-96 h-96 bg-orange-900/15 rounded-full blur-3xl" />
      </div>
      
      <div className="absolute inset-0 bg-grid opacity-[0.02]" />
      
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md relative z-10"
      >
        <Link to="/" className="inline-flex items-center text-neutral-500 hover:text-neutral-300 mb-8 transition text-sm font-medium">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Home
        </Link>
        
        <div className="bg-neutral-900/80 backdrop-blur-xl rounded-3xl shadow-2xl overflow-hidden border border-neutral-800">
          {/* Header */}
          <div className="bg-gradient-to-r from-red-600 via-red-500 to-orange-600 p-8 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-grid opacity-10" />
            <motion.div
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ delay: 0.3, type: 'spring', stiffness: 200 }}
              className="relative z-10 w-20 h-20 bg-white/10 backdrop-blur-md rounded-2xl mx-auto mb-4 flex items-center justify-center border-2 border-white/20 shadow-xl"
            >
              <Shield className="w-10 h-10 text-white" />
            </motion.div>
            <h1 className="text-3xl font-bold text-white mb-2 relative z-10">Admin Access</h1>
            <p className="text-red-100 relative z-10">Restricted area — Authorized personnel only</p>
          </div>
          
          {/* Form */}
          <div className="p-8">
            <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-4 mb-6 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-400/80 text-sm">
                This area is restricted to administrators. All access attempts are logged and monitored for security purposes.
              </p>
            </div>
            
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-neutral-400 mb-2">Admin Email</label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-600" />
                  <input {...register('email')} type="email"
                    className="w-full pl-12 pr-4 py-4 bg-neutral-800/80 border-2 border-neutral-700 text-white rounded-2xl focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all placeholder-neutral-500"
                    placeholder="admin@amrita.edu" />
                </div>
                {errors.email && <p className="text-red-400 text-sm mt-1.5">{errors.email.message}</p>}
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-neutral-400 mb-2">Admin Password</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-600" />
                  <input {...register('password')} type={showPassword ? 'text' : 'password'}
                    className="w-full pl-12 pr-12 py-4 bg-neutral-800/80 border-2 border-neutral-700 text-white rounded-2xl focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all placeholder-neutral-500"
                    placeholder="••••••••" />
                  <button type="button" onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-600 hover:text-neutral-400 transition">
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && <p className="text-red-400 text-sm mt-1.5">{errors.password.message}</p>}
              </div>
              
              <button type="submit" disabled={isSubmitting}
                className="w-full py-4 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 text-white rounded-2xl font-semibold text-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                <Shield className="w-5 h-5" />
                {isSubmitting ? 'Verifying...' : 'Access Admin Panel'}
              </button>
            </form>
            
            <div className="mt-6 text-center">
              <p className="text-neutral-500 text-sm">
                Need user access?{' '}
                <Link to="/login" className="text-red-400 hover:text-red-300 font-semibold">User Login</Link>
              </p>
            </div>
          </div>
        </div>
        
        <p className="text-center text-xs text-neutral-600 mt-6">
          All admin actions are logged and monitored • SpeakEasy ASD Admin v1.0
        </p>
      </motion.div>
    </div>
  )
}

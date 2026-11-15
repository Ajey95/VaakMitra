import { motion, AnimatePresence } from 'framer-motion'
import { X, Mail, Lock, Shield } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authAPI } from '../../services/api'
import { useAuthStore } from '../../store/authStore'
import toast from 'react-hot-toast'

const adminLoginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
})

export default function AdminLoginModal({ isOpen, onClose }) {
  const setAuth = useAuthStore((state) => state.setAuth)
  
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(adminLoginSchema)
  })
  
  const onSubmit = async (data) => {
    try {
      const response = await authAPI.adminLogin(data)
      setAuth(response.data.user, response.data.access_token)
      toast.success('Admin access granted')
      onClose()
      window.location.href = '/admin'
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Admin login failed')
    }
  }
  
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-gradient-to-br from-neutral-800 to-neutral-900 rounded-2xl shadow-2xl z-50 p-8 text-white border border-neutral-700"
          >
            <button
              onClick={onClose}
              className="absolute right-4 top-4 p-2 hover:bg-white/10 rounded-full transition"
            >
              <X className="w-5 h-5" />
            </button>
            
            <div className="flex items-center justify-center mb-6">
              <div className="bg-primary/20 p-4 rounded-full border-2 border-primary">
                <Shield className="w-12 h-12 text-primary" />
              </div>
            </div>
            
            <h2 className="text-2xl font-bold text-center mb-2">Admin Access</h2>
            <p className="text-neutral-400 text-center mb-6 text-sm">Authorized Personnel Only</p>
            
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Admin Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/60" />
                  <input
                    {...register('email')}
                    type="email"
                    className="w-full pl-10 pr-4 py-3 bg-neutral-700/50 border border-neutral-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition text-white placeholder-neutral-400"
                    placeholder="admin@example.com"
                  />
                </div>
                {errors.email && (
                  <p className="text-red-200 text-sm mt-1">{errors.email.message}</p>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">
                  Admin Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/60" />
                  <input
                    {...register('password')}
                    type="password"
                    className="w-full pl-10 pr-4 py-3 bg-neutral-700/50 border border-neutral-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition text-white placeholder-neutral-400"
                    placeholder="••••••••"
                  />
                </div>
                {errors.password && (
                  <p className="text-red-200 text-sm mt-1">{errors.password.message}</p>
                )}
              </div>
              
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-gradient-to-r from-primary to-secondary hover:from-primary-dark hover:to-secondary-dark text-white font-semibold py-3.5 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary/30"
              >
                {isSubmitting ? 'Verifying...' : 'Admin Sign In'}
              </button>
            </form>
            
            <p className="text-center text-neutral-500 text-sm mt-6 flex items-center justify-center gap-2">
              <Shield className="w-4 h-4" />
              Restricted Area
            </p>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

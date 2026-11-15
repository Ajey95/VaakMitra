import { motion, AnimatePresence } from 'framer-motion'
import { X, Mail, Lock, User, Baby, Calendar, Globe } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authAPI } from '../../services/api'
import { useAuthStore } from '../../store/authStore'
import toast from 'react-hot-toast'

const registerSchema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters'),
  child_name: z.string().min(2, 'Child name must be at least 2 characters'),
  child_age: z.coerce.number().min(4, 'Age must be at least 4').max(12, 'Age must be at most 12'),
  email: z.string().email('Invalid email address'),
  password: z.string()
    .min(10, 'Password must be at least 10 characters')
    .regex(/[A-Z]/, 'Password needs an uppercase letter')
    .regex(/[a-z]/, 'Password needs a lowercase letter')
    .regex(/[0-9]/, 'Password needs a number')
    .regex(/[^A-Za-z0-9]/, 'Password needs a special character'),
  confirm_password: z.string().min(1, 'Confirm password is required'),
  language: z.string()
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
})

export default function RegisterModal({ isOpen, onClose, onSwitchToLogin }) {
  const setAuth = useAuthStore((state) => state.setAuth)
  
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      language: 'Tamil'
    }
  })
  
  const onSubmit = async (data) => {
    try {
      const response = await authAPI.register(data)
      
      setAuth(response.data.user, response.data.access_token)
      
      toast.success('Registration successful! Welcome!')
      onClose()
    } catch (error) {
      if (!error.response) {
        toast.error('Cannot reach the server. Please check that the backend is running.')
      } else if (error.response.status === 503) {
        toast.error(error.response.data?.detail || 'Registration is temporarily unavailable. Please try again in a moment.')
      } else {
        toast.error(error.response.data?.detail || 'Registration failed')
      }
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
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 overflow-y-auto"
            onClick={onClose}
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl bg-white rounded-2xl shadow-2xl z-50 max-h-[90vh] overflow-y-auto"
          >
            <div className="bg-gradient-to-r from-primary to-secondary p-6 rounded-t-2xl sticky top-0">
              <button
                onClick={onClose}
                className="absolute right-4 top-4 p-2 hover:bg-white/20 rounded-full transition text-white"
              >
                <X className="w-5 h-5" />
              </button>
              <h2 className="text-2xl font-bold text-white mb-1">Create Account</h2>
              <p className="text-white/90 text-sm">Start your child's speech therapy journey</p>
            </div>
            
            <div className="p-8">
            
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Your Full Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      {...register('full_name')}
                      type="text"
                      className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                      placeholder="John Doe"
                    />
                  </div>
                  {errors.full_name && (
                    <p className="text-red-500 text-sm mt-1">{errors.full_name.message}</p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Child's Name
                  </label>
                  <div className="relative">
                    <Baby className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      {...register('child_name')}
                      type="text"
                      className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                      placeholder="Child's name"
                    />
                  </div>
                  {errors.child_name && (
                    <p className="text-red-500 text-sm mt-1">{errors.child_name.message}</p>
                  )}
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Child's Age (4-12)
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      {...register('child_age')}
                      type="number"
                      min="4"
                      max="12"
                      className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                      placeholder="8"
                    />
                  </div>
                  {errors.child_age && (
                    <p className="text-red-500 text-sm mt-1">{errors.child_age.message}</p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Language
                  </label>
                  <div className="relative">
                    <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <select
                      {...register('language')}
                      className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition appearance-none bg-white"
                    >
                      <option value="Tamil">Tamil</option>
                      <option value="Telugu">Telugu</option>
                      <option value="English">English</option>
                    </select>
                  </div>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    {...register('email')}
                    type="email"
                    className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                    placeholder="your@email.com"
                  />
                </div>
                {errors.email && (
                  <p className="text-red-500 text-sm mt-1">{errors.email.message}</p>
                )}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      {...register('password')}
                      type="password"
                      className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                      placeholder="••••••••"
                    />
                  </div>
                  {errors.password && (
                    <p className="text-red-500 text-sm mt-1">{errors.password.message}</p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      {...register('confirm_password')}
                      type="password"
                      className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                      placeholder="••••••••"
                    />
                  </div>
                  {errors.confirm_password && (
                    <p className="text-red-500 text-sm mt-1">{errors.confirm_password.message}</p>
                  )}
                </div>
              </div>
              
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-gradient-to-r from-primary to-secondary hover:from-primary-dark hover:to-secondary-dark text-white font-semibold py-3.5 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed mt-6 shadow-lg shadow-primary/30"
              >
                {isSubmitting ? 'Creating account...' : 'Create Account'}
              </button>
            </form>
            
            <p className="text-center text-neutral-600 mt-6">
              Already have an account?{' '}
              <button
                onClick={onSwitchToLogin}
                className="text-primary font-semibold hover:text-primary-dark transition"
              >
                Sign in here
              </button>
            </p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

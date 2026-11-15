import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Home, ArrowLeft, Search } from 'lucide-react'

export default function NotFound() {
  const navigate = useNavigate()
  
  const floatingElements = [
    { emoji: '🔍', x: '15%', y: '20%', delay: 0, size: '3rem' },
    { emoji: '❓', x: '80%', y: '15%', delay: 1, size: '2.5rem' },
    { emoji: '🗺️', x: '10%', y: '70%', delay: 0.5, size: '2rem' },
    { emoji: '🧭', x: '85%', y: '75%', delay: 1.5, size: '2.5rem' },
    { emoji: 'அ', x: '25%', y: '85%', delay: 2, size: '2rem' },
    { emoji: '⭐', x: '70%', y: '40%', delay: 0.8, size: '2rem' },
  ]
  
  return (
    <div className="min-h-screen bg-hero relative flex items-center justify-center p-8 overflow-hidden">
      {/* Grid overlay */}
      <div className="absolute inset-0 bg-grid opacity-5 pointer-events-none" />
      
      {/* Gradient orbs */}
      <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 15, repeat: Infinity }}
        className="absolute top-20 left-20 w-72 h-72 bg-primary-500/10 rounded-full blur-3xl" />
      <motion.div animate={{ scale: [1.2, 1, 1.2] }} transition={{ duration: 20, repeat: Infinity }}
        className="absolute bottom-20 right-20 w-96 h-96 bg-secondary-500/10 rounded-full blur-3xl" />
      
      {/* Floating elements */}
      {floatingElements.map((item, i) => (
        <motion.div
          key={i}
          animate={{ y: [-20, 20, -20], rotate: [-5, 5, -5] }}
          transition={{ duration: 6 + i, repeat: Infinity, ease: 'easeInOut', delay: item.delay }}
          className="absolute opacity-30 tamil-letter font-bold"
          style={{ left: item.x, top: item.y, fontSize: item.size, color: 'white' }}
        >
          {item.emoji}
        </motion.div>
      ))}
      
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="text-center relative z-10"
      >
        {/* Animated emoji */}
        <motion.div
          animate={{ y: [0, -30, 0], rotate: [0, 10, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          className="text-[120px] md:text-[160px] leading-none mb-4"
        >
          🤔
        </motion.div>
        
        {/* 404 */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-8xl md:text-9xl font-bold text-white/90 mb-4 tracking-tight"
          style={{ fontFamily: 'Space Grotesk, sans-serif' }}
        >
          4<span className="text-secondary-400">0</span>4
        </motion.h1>
        
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-xl md:text-2xl text-white/70 mb-2"
        >
          Oops! This page seems to have wandered off.
        </motion.p>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-white/40 mb-10 max-w-md mx-auto"
        >
          The page you're looking for doesn't exist or has been moved. Let's get you back on track to your speech therapy journey!
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <button
            onClick={() => navigate('/')}
            className="px-8 py-4 bg-white text-primary-700 rounded-2xl font-bold text-lg shadow-xl hover:shadow-2xl hover:scale-105 transition-all duration-300 flex items-center justify-center gap-2"
          >
            <Home className="w-5 h-5" />
            Go Home
          </button>
          <button
            onClick={() => navigate(-1)}
            className="px-8 py-4 border-2 border-white/25 hover:border-white/50 text-white rounded-2xl font-bold text-lg hover:bg-white/5 transition-all duration-300 flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-5 h-5" />
            Go Back
          </button>
        </motion.div>
        
        {/* SpeakEasy branding */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-12 flex items-center justify-center gap-2 text-white/30 text-sm"
        >
          <div className="w-6 h-6 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-[10px]">SE</span>
          </div>
          SpeakEasy ASD
        </motion.div>
      </motion.div>
    </div>
  )
}

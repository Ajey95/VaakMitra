import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import Confetti from 'react-confetti'
import { useNavigate } from 'react-router-dom'
import { useTherapyStore } from '../../store/therapyStore'
import { progressAPI } from '../../services/api'
import { useAuthStore } from '../../store/authStore'
import toast from 'react-hot-toast'

const motivationalMessages = [
  "🌟 Outstanding! You're a superstar!",
  "🎉 Perfect! You're amazing!",
  "⭐ Incredible work! Keep it up!",
  "🏆 You're a champion!",
  "✨ Brilliant! You did it perfectly!",
  "🎯 Wow! That was perfect!",
  "💫 Excellent! You're on fire!",
  "🌈  Fantastic! You're doing great!"
]

export default function Slide5_Rewards({ lesson }) {
  const navigate = useNavigate()
  const { sessionResults, resetSession } = useTherapyStore()
  const { user, updateUserStats } = useAuthStore()
  const [saved, setSaved] = useState(false)
  
  // Get latest result
  const latestResult = sessionResults[sessionResults.length - 1] || { accuracy: 0 }
  
  // Calculate stars
  const calculateStars = (accuracy) => {
    if (accuracy >= 90) return 3
    if (accuracy >= 70) return 2
    if (accuracy >= 50) return 1
    return 0
  }
  
  const stars = calculateStars(latestResult.accuracy)
  const message = stars >= 2 ? motivationalMessages[Math.floor(Math.random() * motivationalMessages.length)] : "Keep practicing! You're learning! 💪"
  
  useEffect(() => {
    // Save progress
    if (!saved && latestResult.accuracy > 0) {
      saveProgress()
    }
  }, [])
  
  const saveProgress = async () => {
    try {
      const data = {
        lesson_id: lesson.id,
        phoneme: lesson.phoneme,
        lesson_type: lesson.type,
        accuracy: latestResult.accuracy,
        phoneme_match: latestResult.phoneme_match || false,
        mfcc_score: latestResult.mfcc_score || 0,
        gop_score: latestResult.gop_score || 0,
        airflow_score: latestResult.airflow_score || 0,
        feedback: latestResult.feedback || '',
        duration_ms: latestResult.duration_ms || 0
      }
      
      const response = await progressAPI.saveProgress(data)
      
      // Update user stats
      if (user) {
        updateUserStats({
          total_stars: (user.total_stars || 0) + stars,
          total_sessions: (user.total_sessions || 0) + 1
        })
      }
      
      setSaved(true)
      toast.success('Progress saved!')
    } catch (error) {
      console.error('Save error:', error)
    }
  }
  
  const handleTryAgain = () => {
    resetSession()
    window.location.reload()
  }
  
  const handleNextLesson = () => {
    const nextLessonId = lesson.id + 1
    if (nextLessonId <= 6) {
      navigate(`/therapy/${nextLessonId}`)
      window.location.reload()
    } else {
      navigate('/dashboard')
    }
  }
  
  // Map stars to robot mood
  const robotMood = stars === 3 ? 'celebrate' : stars === 2 ? 'happy' : stars === 1 ? 'encourage' : 'thinking'

  return (
    <div className="h-full flex items-center justify-center p-8 relative">
      {stars >= 2 && <Confetti />}
      
      <div className="max-w-4xl w-full">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", duration: 0.6 }}
          className="bg-gradient-to-br from-primary via-secondary to-accent rounded-3xl shadow-2xl p-12 text-white text-center"
        >
          <motion.h1
            initial={{ y: -50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2, type: "spring" }}
            className="text-5xl font-bold mb-8"
          >
            {stars >= 2 ? '🎉 Amazing Work!' : stars === 1 ? '👍 Good Try!' : '💪 Keep Practicing!'}
          </motion.h1>
          
          {/* Stars display */}
          <div className="flex justify-center space-x-4 mb-8">
            {[...Array(3)].map((_, i) => (
              <motion.div
                key={i}
                initial={{ scale: 0, rotate: -180 }}
                animate={{
                  scale: i < stars ? [0, 1.3, 1] : 0.3,
                  rotate: i < stars ? 0 : -180,
                  opacity: i < stars ? 1 : 0.3
                }}
                transition={{
                  delay: 0.5 + i * 0.3,
                  duration: 0.6,
                  type: "spring"
                }}
                className="star-sparkle"
              >
                <div className="text-6xl" role="img" aria-label={i < stars ? `Earned star ${i + 1}` : `Empty star ${i + 1}`}>
                  {i < stars ? '⭐' : '☆'}
                </div>
              </motion.div>
            ))}
          </div>
          
          {/* Score summary card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2 }}
            className="bg-white/20 backdrop-blur rounded-2xl p-8 mb-8"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-3xl font-bold">{lesson.symbol}</div>
                <div className="text-sm opacity-80">Lesson</div>
              </div>
              
              <div>
                <div className="text-3xl font-bold">{Math.round(latestResult.accuracy)}%</div>
                <div className="text-sm opacity-80">Accuracy</div>
              </div>
              
              <div>
                <div className="text-3xl">{latestResult.phoneme_match ? '✅' : '❌'}</div>
                <div className="text-sm opacity-80">Match</div>
              </div>
              
              <div>
                <div className="text-3xl font-bold">{stars} ⭐</div>
                <div className="text-sm opacity-80">Stars Earned</div>
              </div>
            </div>
          </motion.div>
          
          {/* Motivational message */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            className="text-2xl mb-8"
          >
            {message}
          </motion.p>
          
          {/* Total stars today */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.7 }}
            className="mb-8"
          >
            <p className="text-lg opacity-90 mb-2">Total Stars Today</p>
            <div className="flex justify-center items-center space-x-2">
              <div className="h-4 bg-white/20 rounded-full w-64 overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-accent to-accent-dark"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min((user?.total_stars || 0) / 18 * 100, 100)}%` }}
                  transition={{ delay: 1.8, duration: 1 }}
                />
              </div>
              <span className="font-bold text-xl">{user?.total_stars || 0}/18</span>
            </div>
          </motion.div>
          
          {/* Action buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 2 }}
            className="flex flex-col sm:flex-row justify-center gap-4"
          >
            <button
              onClick={handleTryAgain}
              className="px-8 py-4 bg-white/20 hover:bg-white/30 backdrop-blur border-2 border-white rounded-full transition font-bold text-lg"
            >
              🔄 Try Again
            </button>
            
            {lesson.id < 6 && (
              <button
                onClick={handleNextLesson}
                className="px-8 py-4 bg-white text-primary hover:bg-gray-100 rounded-full transition font-bold text-lg"
              >
                ➡️ Next Lesson
              </button>
            )}
            
            <button
              onClick={() => navigate('/dashboard')}
              className="px-8 py-4 bg-white/20 hover:bg-white/30 backdrop-blur border-2 border-white rounded-full transition font-bold text-lg"
            >
              🏠 Dashboard
            </button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

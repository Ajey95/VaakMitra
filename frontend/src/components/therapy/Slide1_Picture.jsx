import { motion } from 'framer-motion'
import { Volume2 } from 'lucide-react'
import { getPippinTargetText } from '../../features/pippin/trainingPippin'
import { repeatPhrase } from '../../utils/speechRepeat'

export default function Slide1_Picture({ lesson, onNext, silent = false }) {
  const playAudio = () => {
    repeatPhrase(getPippinTargetText(lesson), { lang: 'en-IN' })
  }
  
  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="max-w-6xl w-full">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="grid lg:grid-cols-2 gap-8 bg-white rounded-3xl shadow-2xl overflow-hidden"
        >
          {/* Left panel - Tamil letter/word */}
          <div className="bg-gradient-to-br from-primary to-primary-dark p-12 flex flex-col items-center justify-center relative overflow-hidden">
            {/* Sparkle animations */}
            {!silent && [...Array(6)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-2 h-2 bg-white rounded-full"
                initial={{
                  x: Math.random() * 400,
                  y: Math.random() * 400,
                  scale: 0
                }}
                animate={{
                  scale: [0, 1, 0],
                  opacity: [0, 1, 0]
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  delay: i * 0.3
                }}
              />
            ))}
            
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", delay: 0.2 }}
              className="relative z-10"
            >
              <div className="text-9xl tamil-letter font-bold text-white mb-4 text-center">
                {lesson.symbol}
              </div>
              
              <div className="text-5xl font-bold text-white/90 text-center mb-6">
                {lesson.english}
              </div>
              
              {!silent && <div className="flex justify-center space-x-1">
                {[...Array(lesson.difficulty)].map((_, i) => (
                  <motion.span
                    key={i}
                    initial={{ scale: 0, rotate: -180 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ delay: 0.5 + i * 0.1, type: "spring" }}
                    className="text-3xl"
                  >
                    ⭐
                  </motion.span>
                ))}
              </div>}
            </motion.div>
          </div>
          
          {/* Right panel - Image */}
          <div className="p-12 flex flex-col items-center justify-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="w-full"
            >
              {/* Built-in visual: lessons must not depend on optional image files. */}
              <div
                data-testid="lesson-built-in-visual"
                role="img"
                aria-label={`${lesson.english} pronunciation symbol`}
                className="w-full aspect-square bg-gradient-to-br from-secondary/20 to-accent/20 rounded-3xl flex flex-col items-center justify-center mb-6 overflow-hidden"
              >
                <div className="tamil-letter text-9xl font-bold text-primary mb-4">
                  {lesson.type === 'word'
                    ? (lesson.phoneme === 'amma' ? '👩' : lesson.phoneme === 'appa' ? '👨' : '💬')
                    : lesson.symbol}
                </div>
                <div className="text-3xl font-bold text-gray-700">{lesson.english}</div>
              </div>
              
              <p className="text-center text-gray-600 mb-6 italic">
                {silent ? 'Look at the symbol at your own pace. This letter is not word-scored.' : 'Look at the symbol, then listen and repeat the sound.'}
              </p>
              
              {!silent && <button
                onClick={playAudio}
                className="w-full bg-secondary hover:bg-secondary-dark text-white font-bold py-4 rounded-2xl transition flex items-center justify-center space-x-2 mb-4"
              >
                <Volume2 className="w-6 h-6" />
                <span>Listen</span>
              </button>}
              
              {!silent && <motion.div
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="text-center text-gray-500 text-sm"
              >
                👆 Tap to hear it again!
              </motion.div>}
              {silent && <p className="text-sm text-center text-neutral-500">An approved local voice example is not installed here.</p>}
            </motion.div>
          </div>
        </motion.div>
        
        {/* Next button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-center mt-8"
        >
          <button
            onClick={onNext}
            className="px-12 py-4 bg-gradient-to-r from-primary to-secondary hover:from-primary-dark hover:to-secondary-dark text-white font-bold rounded-full transition shadow-lg"
          >
            Next →
          </button>
        </motion.div>
      </div>
    </div>
  )
}

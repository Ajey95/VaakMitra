import { motion } from 'framer-motion'
import { ArrowRight, PlayCircle} from 'lucide-react'
import { Link } from 'react-scroll'

export default function HeroSection({ onRegisterClick }) {
  return (
    <section id="home" className="min-h-screen bg-hero pt-20 relative overflow-hidden">
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-white/20 rounded-full"
            initial={{
              x: Math.random() * window.innerWidth,
              y: Math.random() * window.innerHeight,
            }}
            animate={{
              y: [null, Math.random() * window.innerHeight],
              opacity: [0.2, 0.5, 0.2],
            }}
            transition={{
              duration: Math.random() * 10 + 10,
              repeat: Infinity,
              ease: "linear"
            }}
          />
        ))}
      </div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left side - Content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
          >
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center bg-white/20 backdrop-blur px-4 py-2 rounded-full text-white mb-6"
            >
              <span className="text-2xl mr-2">🎯</span>
              <span className="font-semibold">AI-Powered Speech Therapy</span>
            </motion.div>
            
            <h1 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
              Every Child Has A Voice.{' '}
              <span className="text-accent">Let's Find It Together.</span>
            </h1>
            
            <p className="text-xl text-white/90 mb-8 leading-relaxed">
              Privacy-first, edge-based speech therapy for ASD children. 
              Personalized. Gamified. Effective.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 mb-8">
              <button
                onClick={onRegisterClick}
                className="px-8 py-4 bg-white text-primary rounded-full hover:bg-gray-100 transition font-bold text-lg shadow-xl flex items-center justify-center group"
              >
                Start Free Today
                <ArrowRight className="ml-2 group-hover:translate-x-1 transition" />
              </button>
              
              <Link
                to="how-it-works"
                smooth={true}
                duration={500}
                className="px-8 py-4 border-2 border-white text-white rounded-full hover:bg-white hover:text-primary transition font-bold text-lg flex items-center justify-center cursor-pointer"
              >
                <PlayCircle className="mr-2" />
                See How It Works
              </Link>
            </div>
            
            {/* Stats row */}
            <div className="grid grid-cols-4 gap-4">
              {[
                { value: '4', label: 'Letters' },
                { value: '2', label: 'Words' },
                { value: 'AI', label: 'Real-time' },
                { value: '100%', label: 'Private' }
              ].map((stat, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                  className="text-center bg-white/10 backdrop-blur rounded-xl p-3"
                >
                  <div className="text-2xl font-bold text-white">{stat.value}</div>
                  <div className="text-sm text-white/80">{stat.label}</div>
                </motion.div>
              ))}
            </div>
          </motion.div>
          
          {/* Right side - Illustration */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative"
          >
            <div className="relative">
              {/* Placeholder illustration */}
              <div className="w-full aspect-square bg-white/10 backdrop-blur rounded-3xl flex items-center justify-center relative overflow-hidden">
                <motion.div
                  animate={{
                    scale: [1, 1.2, 1],
                    rotate: [0, 5, -5, 0]
                  }}
                  transition={{
                    duration: 4,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                  className="text-8xl"
                >
                  🎙️
                </motion.div>
                
                {/* Floating Tamil letters */}
                {['அ', 'ல', 'த', 'ஆ'].map((letter, i) => (
                  <motion.div
                    key={i}
                    className="absolute tamil-letter text-4xl font-bold text-white/80"
                    initial={{
                      x: [120, -120][i % 2] * (i % 2 === 0 ? 1 : -1),
                      y: 100 + i * 80,
                    }}
                    animate={{
                      y: [null, (100 + i * 80) - 20, (100 + i * 80)],
                    }}
                    transition={{
                      duration: 2 + i * 0.5,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  >
                    {letter}
                  </motion.div>
                ))}
              </div>
              
              {/* Sound waves */}
              <div className="absolute -right-4 top-1/2 -translate-y-1/2">
                {[...Array(3)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="w-20 h-20 border-4 border-white/30 rounded-full absolute"
                    initial={{ scale: 0.5, opacity: 0.8 }}
                    animate={{ scale: 2, opacity: 0 }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      delay: i * 0.6
                    }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
      
      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      >
        <div className="w-6 h-10 border-2 border-white rounded-full flex justify-center pt-2">
          <div className="w-1 h-3 bg-white rounded-full" />
        </div>
      </motion.div>
    </section>
  )
}

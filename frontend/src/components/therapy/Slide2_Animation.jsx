import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Play, Pause, RotateCcw, Mic, Volume2, Video } from 'lucide-react'
import { getPippinTargetText } from '../../features/pippin/trainingPippin'
import { stopCharacterSpeech } from '../../features/characters/characterVoice'
import { repeatPhrase } from '../../utils/speechRepeat'

// Import pronunciation video
import pronunciationAVideo from '../../assets/videos/pronounciation_a.mp4'

function SilentTeachingStep({ lesson, onNext, onPrev }) {
  return <div className="h-full flex items-center justify-center p-8">
    <div className="max-w-4xl w-full bg-white rounded-3xl shadow-2xl p-8 md:p-12">
      <h2 className="text-4xl font-bold text-center mb-8 gradient-text">Visual practice</h2>
      <div className="bg-gradient-to-br from-gray-100 to-gray-200 rounded-3xl p-8 mb-8">
        <div className="aspect-video bg-white rounded-2xl flex items-center justify-center shadow-2xl">
          <span className="tamil-letter text-8xl md:text-9xl font-bold text-primary">{lesson.symbol}</span>
        </div>
      </div>
      <p className="text-center text-gray-700 mb-6">Look at the letter at your own pace. It is not graded as a word.</p>
      <p className="text-center text-neutral-500 text-sm mb-8">No approved local audio prompt is installed for this activity.</p>
      <div className="flex justify-between gap-4">
        <button onClick={onPrev} className="px-8 py-3 border-2 border-gray-300 hover:border-primary text-gray-700 hover:text-primary rounded-full font-semibold">← Back</button>
        <button onClick={onNext} className="px-8 py-3 bg-gradient-to-r from-primary to-secondary text-white rounded-full font-semibold">Finish</button>
      </div>
    </div>
  </div>
}

export default function Slide2_Animation({ lesson, onNext, onPrev, silent = false }) {
  if (silent) return <SilentTeachingStep lesson={lesson} onNext={onNext} onPrev={onPrev} />
  return <LegacyAnimation lesson={lesson} onNext={onNext} onPrev={onPrev} />
}

function LegacyAnimation({ lesson, onNext, onPrev }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [videoAvailable, setVideoAvailable] = useState(false)
  const [videoError, setVideoError] = useState(false)
  const videoRef = useRef(null)
  
  // Map phoneme to video path - for now we have video for 'a'
  const videoMap = {
    'a': pronunciationAVideo,
    // Add more videos as they become available
    // 'aa': pronunciationAaVideo,
    // 'la': pronunciationLaVideo,
  }
  
  const videoPath = videoMap[lesson.phoneme] || null
  
  // Check if video exists
  useEffect(() => {
    if (videoPath) {
      setVideoAvailable(true)
      console.log('✅ Video available for phoneme:', lesson.phoneme, videoPath)
    } else {
      setVideoAvailable(false)
      console.log('⚠️ No video available for phoneme:', lesson.phoneme)
    }
  }, [lesson.phoneme, videoPath])
  
  const playPippinTarget = () => {
    const spoken = repeatPhrase(getPippinTargetText(lesson), {
      lang: 'en-IN',
      onStart: () => setIsPlaying(true),
      onEnd: () => setIsPlaying(false),
      onError: () => setIsPlaying(false),
    })
    if (!spoken) setIsPlaying(false)
  }

  const handlePlayVideo = async () => {
    if (videoRef.current && videoAvailable) {
      try {
        await videoRef.current.play()
        setIsPlaying(true)
      } catch {
        setVideoError(true)
        playPippinTarget()
      }
    } else {
      playPippinTarget()
    }
  }
  
  const handlePause = () => {
    if (videoRef.current && videoAvailable) {
      videoRef.current.pause()
    } else {
      stopCharacterSpeech()
    }
    setIsPlaying(false)
  }
  
  const handleReplay = async () => {
    if (videoRef.current && videoAvailable) {
      videoRef.current.currentTime = 0
      await handlePlayVideo()
    } else {
      playPippinTarget()
    }
  }

  useEffect(() => () => stopCharacterSpeech(), [])
  
  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="max-w-4xl w-full">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-3xl shadow-2xl p-12"
        >
          <motion.h2
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="text-4xl font-bold text-center mb-8 gradient-text"
          >
            Watch & Learn Pronunciation!
          </motion.h2>
          
          {videoAvailable && (
            <div className="flex justify-center mb-4">
              <div className="inline-flex items-center bg-green-100 text-green-700 px-4 py-2 rounded-full">
                <Video className="w-5 h-5 mr-2" />
                <span className="font-semibold">HD Training Video Available</span>
              </div>
            </div>
          )}
          
          {/* Video/Animation container */}
          <div className="bg-gradient-to-br from-gray-100 to-gray-200 rounded-3xl p-8 mb-8">
            <div className="aspect-video bg-white rounded-2xl flex items-center justify-center overflow-hidden relative shadow-2xl">
              
              {videoAvailable && !videoError ? (
                /* Professional pronunciation video from assets */
                <video
                  ref={videoRef}
                  src={videoPath}
                  className="w-full h-full object-cover rounded-lg"
                  onEnded={() => setIsPlaying(false)}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onError={(e) => {
                    console.error('Video error:', e)
                    setVideoError(true)
                  }}
                  controls={false}
                  playsInline
                />
              ) : (
                /* Fallback: GIF animation */
                <>
                  <img
                    src={lesson.mouth}
                    alt={`${lesson.english} mouth animation`}
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      e.target.style.display = 'none'
                      e.target.nextElementSibling.style.display = 'flex'
                    }}
                  />
                  
                  {/* CSS fallback animation */}
                  <div className="hidden w-full h-full items-center justify-center flex-col">
                    <div className="relative mb-4">
                      <div className="w-32 h-24 bg-pink-300 rounded-full relative">
                        <div className="absolute inset-x-6 top-1/2 -translate-y-1/2 h-8 bg-red-400 rounded-full mouth-animate" />
                      </div>
                    </div>
                    <p className="text-center text-gray-600 font-bold text-5xl mb-2">{lesson.symbol}</p>
                    <p className="text-center text-gray-600 font-semibold text-2xl">{lesson.english}</p>
                  </div>
                </>
              )}
            </div>
            
            {!videoAvailable && (
              <div className="mt-4 text-center text-sm text-blue-700 bg-blue-50 py-3 px-4 rounded-lg border border-blue-200">
                ℹ️ Video available only for letter 'அ' (a). More pronunciation videos coming soon!
              </div>
            )}
          </div>
          
          {/* Phoneme steps */}
          <div className="flex justify-center space-x-4 mb-8">
            {['Step 1', 'Step 2', 'Done'].map((step, i) => (
              <motion.div
                key={i}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3 + i * 0.1 }}
                className={`px-6 py-2 rounded-full font-semibold ${
                  i === 0 ? 'bg-primary text-white' :
                  i === 1 ? 'bg-secondary text-white' :
                  'bg-accent text-white'
                }`}
              >
                {step}
              </motion.div>
            ))}
          </div>
          
          {/* Tip card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-gradient-to-r from-primary/10 to-secondary/10 rounded-2xl p-6 mb-8"
          >
            <p className="text-lg text-gray-700 font-medium text-center">
              💡 <strong>Tip:</strong> {lesson.tip}
            </p>
          </motion.div>
          
          {/* Control buttons */}
          <div className="flex justify-center space-x-4 mb-8">
            {!isPlaying ? (
              <button
                onClick={handlePlayVideo}
                className="px-10 py-4 bg-gradient-to-r from-primary to-secondary hover:from-primary-dark hover:to-secondary-dark text-white rounded-xl transition flex items-center space-x-2 font-bold text-lg shadow-lg"
              >
                <Play className="w-6 h-6" />
                <span>Play {videoAvailable ? 'Video' : 'Audio'}</span>
              </button>
            ) : (
              <button
                onClick={handlePause}
                className="px-10 py-4 bg-red-500 hover:bg-red-600 text-white rounded-xl transition flex items-center space-x-2 font-bold text-lg shadow-lg"
              >
                <Pause className="w-6 h-6" />
                <span>Pause</span>
              </button>
            )}
            
            <button
              onClick={handleReplay}
              className="px-8 py-4 bg-gray-200 hover:bg-gray-300 rounded-xl transition flex items-center space-x-2 font-semibold"
            >
              <RotateCcw className="w-5 h-5" />
              <span>Replay</span>
            </button>
          </div>
          
          {/* Navigation */}
          <div className="flex justify-between">
            <button
              onClick={onPrev}
              className="px-8 py-3 border-2 border-gray-300 hover:border-primary text-gray-700 hover:text-primary rounded-full transition font-semibold"
            >
              ← Back
            </button>
            
            <button
              onClick={onNext}
              className="px-8 py-3 bg-gradient-to-r from-primary to-secondary hover:from-primary-dark hover:to-secondary-dark text-white rounded-full transition font-semibold flex items-center space-x-2"
            >
              <Mic className="w-5 h-5" />
              <span>I'm Ready!</span>
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

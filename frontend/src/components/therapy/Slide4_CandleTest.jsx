import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, Square, RotateCcw, Wind } from 'lucide-react'
import Confetti from 'react-confetti'
import CandleScene from '../three/CandleScene'
import { useAudioRecorder } from '../../hooks/useAudioRecorder'
import toast from 'react-hot-toast'

// appa = plosive → blow the flame out (high airflow). amma = soft nasal → keep it lit (gentle).
const BLOW_OUT = 0.6
const GENTLE_MIN = 0.08

export default function Slide4_CandleTest({ lesson, onNext, onPrev }) {
  const blowsOut = lesson.candleBlows ?? (lesson.phoneme === 'appa')
  const [airflowScore, setAirflowScore] = useState(0)
  const [peak, setPeak] = useState(0)
  const [showConfetti, setShowConfetti] = useState(false)
  const [result, setResult] = useState(null) // 'success' | 'tooSoft' | 'tooStrong' | null
  const peakRef = useRef(0)

  const { isRecording, analyserRef, startRecording, stopRecording, resetRecording } = useAudioRecorder()

  // Real-time airflow from the live microphone signal
  useEffect(() => {
    if (!isRecording) return
    const id = setInterval(() => {
      const analyser = analyserRef?.current
      if (!analyser) return
      const data = new Uint8Array(analyser.frequencyBinCount)
      analyser.getByteFrequencyData(data)
      const avg = data.reduce((a, b) => a + b, 0) / data.length / 255
      // Boost so a strong plosive can realistically reach "blow-out" territory
      const airflow = Math.min(1, avg * 2.4)
      setAirflowScore(airflow)
      if (airflow > peakRef.current) {
        peakRef.current = airflow
        setPeak(airflow)
      }
    }, 60)
    return () => clearInterval(id)
  }, [isRecording, analyserRef])

  const handleStart = async () => {
    setResult(null)
    setShowConfetti(false)
    peakRef.current = 0
    setPeak(0)
    setAirflowScore(0)
    const ok = await startRecording(lesson.language || 'en-IN')
    if (ok) toast.success(blowsOut ? 'Blow it out — say APPA!' : 'Gently now — say AMMA!')
  }

  const handleStop = () => {
    stopRecording()
    const p = peakRef.current
    let outcome
    if (blowsOut) {
      outcome = p >= BLOW_OUT ? 'success' : 'tooSoft'
    } else {
      // amma: must be audible but stay gentle (don't blow the flame out)
      if (p < GENTLE_MIN) outcome = 'tooSoft'
      else if (p >= BLOW_OUT) outcome = 'tooStrong'
      else outcome = 'success'
    }
    setResult(outcome)
    if (outcome === 'success') {
      setShowConfetti(true)
      // settle the flame to a clear final state
      setAirflowScore(blowsOut ? 1 : 0.25)
    }
  }

  const handleReset = () => {
    resetRecording()
    setResult(null)
    setShowConfetti(false)
    peakRef.current = 0
    setPeak(0)
    setAirflowScore(0)
  }

  const tip = blowsOut
    ? 'Say APPA with a strong "P" — push the air hard to blow the candle out! 💨'
    : 'Say AMMA softly and gently — keep the candle flame alive! 🕯️'

  const statusText = () => {
    if (result === 'success') return blowsOut ? '🎉 Perfect! You blew it out!' : '🎉 Beautiful! You kept it gently lit!'
    if (result === 'tooSoft') return blowsOut ? '💪 A bit stronger! Push more air for the "P".' : '🔈 A little louder — but stay gentle!'
    if (result === 'tooStrong') return '🌬️ Too strong! Say AMMA more softly so the flame survives.'
    if (isRecording) return blowsOut ? 'Blow hard now… 💨' : 'Gently… keep it soft 🍃'
    return 'Tap the mic and say the word out loud'
  }

  return (
    <div className="h-full flex items-center justify-center p-6 md:p-8 relative">
      {showConfetti && <Confetti numberOfPieces={250} recycle={false} gravity={0.25} />}

      <div className="max-w-5xl w-full">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-3xl shadow-2xl p-6 md:p-8"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-3 gradient-text">
            Candle Breath Test
          </h2>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.15 }}
            className="bg-gradient-to-r from-accent/15 to-secondary/15 rounded-2xl p-5 mb-6"
          >
            <p className="text-lg text-center text-neutral-700 font-medium">{tip}</p>
          </motion.div>

          <CandleScene airflowScore={airflowScore} word={lesson.phoneme} />

          {/* Live readout */}
          <div className="mt-6 max-w-md mx-auto">
            <div className="flex items-center justify-between text-sm mb-1.5">
              <span className="flex items-center gap-1.5 font-medium text-neutral-600">
                <Wind className="w-4 h-4" /> Breath strength
              </span>
              <span className="font-bold text-neutral-800">{Math.round(airflowScore * 100)}%</span>
            </div>
            <div className="h-3.5 bg-neutral-200 rounded-full overflow-hidden relative">
              {/* blow-out marker */}
              <div className="absolute inset-y-0 z-10" style={{ left: `${BLOW_OUT * 100}%` }}>
                <div className="w-px h-full bg-coral-500/70" />
              </div>
              <motion.div
                className={`h-full rounded-full ${blowsOut ? 'bg-gradient-to-r from-sky-400 via-amber-400 to-coral-500' : 'bg-gradient-to-r from-emerald-400 to-teal-500'}`}
                animate={{ width: `${airflowScore * 100}%` }}
                transition={{ duration: 0.08 }}
              />
            </div>
            <p className="text-[11px] text-neutral-400 mt-1 text-right">Peak: {Math.round(peak * 100)}%</p>
          </div>

          {/* Status + controls */}
          <div className="mt-6 text-center space-y-4">
            <p className={`text-lg font-semibold ${result === 'success' ? 'text-accent-600' : result ? 'text-gold-600' : 'text-neutral-600'}`}>
              {statusText()}
            </p>

            <div className="flex justify-center gap-3">
              {!isRecording && result !== 'success' && (
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={result ? handleReset : handleStart}
                  className="px-8 py-3.5 bg-gradient-to-r from-primary to-secondary text-white font-bold rounded-full transition shadow-lg shadow-primary/30 inline-flex items-center gap-2"
                >
                  {result ? <><RotateCcw className="w-5 h-5" /> Try Again</> : <><Mic className="w-5 h-5" /> Start Breath Test</>}
                </motion.button>
              )}

              {isRecording && (
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={handleStop}
                  className="px-8 py-3.5 bg-coral-500 hover:bg-coral-600 text-white font-bold rounded-full transition shadow-lg inline-flex items-center gap-2"
                >
                  <Square className="w-5 h-5 fill-white" /> Stop & Check
                </motion.button>
              )}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between mt-8 pt-6 border-t border-neutral-100">
            <button
              onClick={onPrev}
              className="px-8 py-3 border-2 border-neutral-300 hover:border-primary text-neutral-700 hover:text-primary rounded-full transition font-semibold"
            >
              ← Back
            </button>

            <AnimatePresence>
              {result === 'success' && (
                <motion.button
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  whileHover={{ scale: 1.03 }}
                  onClick={onNext}
                  className="px-10 py-3 bg-gradient-to-r from-primary to-secondary text-white rounded-full transition font-semibold shadow-lg shadow-primary/30"
                >
                  Continue → 🎉
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

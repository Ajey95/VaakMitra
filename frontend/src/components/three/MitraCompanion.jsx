/**
 * MitraCompanion.jsx
 * ──────────────────────────────────────────────────────────────────
 * Floating MITRA robot companion for therapy slides.
 * Reacts to slide context and score in real-time.
 *
 * Props:
 *   slide       1-5  (current slide number)
 *   score       0-100 (evaluation score — drives mood)
 *   audioLevel  0-1   (mic amplitude)
 *   isRecording bool
 *   compact     bool  (smaller size for inline use)
 * ──────────────────────────────────────────────────────────────────
 */

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import MitraRobot from './MitraRobot'

// ── Per-slide messages ─────────────────────────────────────────────
const SLIDE_MESSAGES = {
  1: [
    "Let's learn this together! 🌟",
    "Look carefully at the letter!",
    "Ready to practice? I'm here!",
  ],
  2: [
    "Watch the mouth movements!",
    "See how it's pronounced?",
    "Copy what you see! You can do it!",
  ],
  3: [
    "Your turn! Speak clearly 🎤",
    "I'm listening carefully...",
    "Great effort! Keep going!",
    "Take a deep breath first!",
  ],
  4: [
    "Blow the candle gently!",
    "Control your breath... slowly!",
    "Almost there! Try again!",
  ],
  5: [
    "Amazing work today! 🏆",
    "You're a star learner! ⭐",
    "I'm so proud of you! 🎉",
  ],
}

const SCORE_MOOD = (score) => {
  if (score >= 85) return 'celebrate'
  if (score >= 65) return 'happy'
  if (score >= 40) return 'encourage'
  if (score > 0)  return 'thinking'
  return null
}

const SLIDE_MOOD = {
  1: 'idle',
  2: 'happy',
  3: 'listen',
  4: 'thinking',
  5: 'celebrate',
}

export default function MitraCompanion({
  slide = 1,
  score = null,
  audioLevel = 0,
  isRecording = false,
  compact = false,
}) {
  const [currentMessage, setCurrentMessage] = useState('')
  const [showMessage, setShowMessage] = useState(false)
  const [mood, setMood] = useState(SLIDE_MOOD[slide] || 'idle')
  const messageTimerRef = useRef(null)
  const msgIndexRef = useRef(0)

  // Cycle through slide messages
  const rotateMessage = (msgs) => {
    const msg = msgs[msgIndexRef.current % msgs.length]
    msgIndexRef.current++
    setCurrentMessage(msg)
    setShowMessage(true)
    if (messageTimerRef.current) clearTimeout(messageTimerRef.current)
    messageTimerRef.current = setTimeout(() => setShowMessage(false), 3500)
  }

  // React to slide changes
  useEffect(() => {
    msgIndexRef.current = 0
    const baseMood = SLIDE_MOOD[slide] || 'idle'
    setMood(isRecording ? 'listen' : baseMood)
    const msgs = SLIDE_MESSAGES[slide] || SLIDE_MESSAGES[1]
    rotateMessage(msgs)
    // Rotate messages every 8s while on this slide
    const interval = setInterval(() => rotateMessage(msgs), 8000)
    return () => {
      clearInterval(interval)
      if (messageTimerRef.current) clearTimeout(messageTimerRef.current)
    }
  }, [slide])

  // React to recording state
  useEffect(() => {
    if (isRecording) {
      setMood('listen')
      setCurrentMessage("I'm listening carefully... 👂")
      setShowMessage(true)
    } else if (SLIDE_MOOD[slide]) {
      setMood(SLIDE_MOOD[slide])
    }
  }, [isRecording, slide])

  // React to score
  useEffect(() => {
    if (score === null) return
    const scoreMood = SCORE_MOOD(score)
    if (scoreMood) {
      setMood(scoreMood)
      if (score >= 85) {
        setCurrentMessage(`Excellent! ${score}% accuracy! 🎉`)
      } else if (score >= 65) {
        setCurrentMessage(`Good job! ${score}% — keep it up! 😊`)
      } else if (score >= 40) {
        setCurrentMessage(`${score}% — You're improving! 💪`)
      } else {
        setCurrentMessage(`${score}% — Let's try again! 🤗`)
      }
      setShowMessage(true)
      if (messageTimerRef.current) clearTimeout(messageTimerRef.current)
      messageTimerRef.current = setTimeout(() => setShowMessage(false), 4000)
    }
  }, [score])

  const size = compact ? 220 : 300

  return (
    <div className="flex flex-col items-center select-none">
      {/* Speech bubble */}
      <AnimatePresence>
        {showMessage && currentMessage && (
          <motion.div
            key={currentMessage}
            initial={{ opacity: 0, y: 8, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 300, damping: 24 }}
            className="relative mb-2 px-4 py-2.5 rounded-2xl text-center text-sm font-semibold text-neutral-800 shadow-lg max-w-[200px]"
            style={{
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(12px)',
              border: '2px solid rgba(99,102,241,0.25)',
              boxShadow: '0 8px 32px rgba(99,102,241,0.15)',
            }}
          >
            {currentMessage}
            {/* Bubble tail */}
            <div
              className="absolute left-1/2 -translate-x-1/2 -bottom-2.5"
              style={{
                width: 0,
                height: 0,
                borderLeft: '8px solid transparent',
                borderRight: '8px solid transparent',
                borderTop: '10px solid rgba(99,102,241,0.25)',
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* 3D Robot */}
      <MitraRobot
        mood={mood}
        audioLevel={isRecording ? audioLevel : 0}
        size={size}
        zoom={compact ? 1.2 : 1}
      />

      {/* Recording pulse ring */}
      {isRecording && (
        <motion.div
          className="absolute rounded-full border-2 border-violet-400 pointer-events-none"
          style={{ width: size * 0.85, height: size * 0.85, top: '10%' }}
          animate={{ scale: [1, 1.08, 1], opacity: [0.5, 0.2, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}
    </div>
  )
}

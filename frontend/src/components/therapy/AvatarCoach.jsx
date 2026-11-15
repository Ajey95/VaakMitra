import { useCallback, useEffect, useMemo, useState } from 'react'
import { Volume2, VolumeX, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { useSettingsStore } from '../../store/settingsStore'
import {
  APPLICATION_VOICE_PROFILE_ID,
  speakCharacter,
  stopCharacterSpeech,
} from '../../features/characters/characterVoice'
import {
  canSpeakWithBrowser,
  getAvatarCoachMessage,
  getAvatarCoachMood,
  getAvatarCoachName,
} from '../../utils/avatarCoach'

export default function AvatarCoach({
  lesson,
  slide = 1,
  outcome = null,
  isRecording = false,
  audioLevel = 0,
  compact = false,
}) {
  const { soundEnabled, autoPlay } = useSettingsStore()
  const [isSpeaking, setIsSpeaking] = useState(false)
  const browserSpeech = useMemo(() => canSpeakWithBrowser(), [])
  const message = getAvatarCoachMessage({ slide, lesson, outcome })
  const mood = getAvatarCoachMood({ slide, outcome, isRecording })
  const name = getAvatarCoachName(lesson)
  const activity = Math.max(audioLevel, isSpeaking ? 0.35 : 0)

  const speak = useCallback(() => {
    if (!browserSpeech || !soundEnabled) return

    speakCharacter(message, {
      profileId: APPLICATION_VOICE_PROFILE_ID,
      guided: true,
      language: lesson?.avatar_coach?.voice || 'en-IN',
      enabled: soundEnabled,
      onStart: () => setIsSpeaking(true),
      onEnd: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
    })
  }, [browserSpeech, lesson, message, soundEnabled])

  useEffect(() => {
    if (autoPlay && soundEnabled) speak()
    return () => {
      if (browserSpeech) stopCharacterSpeech()
      setIsSpeaking(false)
    }
  }, [autoPlay, browserSpeech, message, soundEnabled, speak])

  return (
    <div className={`flex flex-col items-center select-none ${compact ? 'w-[220px]' : 'w-full max-w-[280px]'}`}>
      <motion.div
        key={message}
        initial={{ opacity: 0, y: 8, scale: 0.94 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="relative mb-1.5 w-full rounded-2xl border-2 border-primary-200 bg-white/95 px-3 py-2 text-center text-xs font-semibold text-neutral-800 shadow-lg backdrop-blur"
      >
        <span className="mr-1" aria-hidden="true">{mood === 'celebrate' ? '🎉' : mood === 'listen' ? '👂' : '🤖'}</span>
        {message}
        <div className="absolute -bottom-2 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-b-2 border-r-2 border-primary-200 bg-white" />
      </motion.div>

      <motion.div
        className={`relative overflow-hidden rounded-3xl border-4 border-white/90 bg-gradient-to-br from-indigo-100 via-white to-cyan-100 shadow-xl ${compact ? 'h-[190px] w-[220px]' : 'h-[250px] w-full'}`}
        animate={{ y: isSpeaking || isRecording ? [0, -4, 0] : 0, scale: isSpeaking ? [1, 1.02, 1] : 1 }}
        transition={{ duration: 1.2, repeat: isSpeaking || isRecording ? Infinity : 0, ease: 'easeInOut' }}
      >
        <img
          src="/assets/livetalk-avatar.png"
          alt="LiveTalk avatar coach"
          className="h-full w-full object-cover object-top"
        />
        <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-indigo-950/45 to-transparent" />
        <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-end gap-1 rounded-full bg-black/45 px-3 py-1.5 backdrop-blur">
          {[0, 1, 2, 3, 4].map((bar) => (
            <motion.span
              key={bar}
              className="w-1 rounded-full bg-white"
              animate={{ height: activity > 0 ? [5, 8 + activity * 18 + ((bar + 1) % 3) * 4, 5] : 5 }}
              transition={{ duration: 0.45, repeat: isSpeaking || isRecording ? Infinity : 0, delay: bar * 0.06 }}
            />
          ))}
        </div>
        {(isSpeaking || isRecording) && (
          <span className="absolute right-3 top-3 rounded-full bg-emerald-500 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-white shadow">
            {isRecording ? 'Listening' : 'Speaking'}
          </span>
        )}
      </motion.div>

      <div className="-mt-4 flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 text-[11px] font-bold text-primary-700 shadow-sm backdrop-blur">
        <Sparkles className="h-3.5 w-3.5" />
        <span>{name} · LiveTalk coach</span>
        <button
          type="button"
          onClick={speak}
          disabled={!browserSpeech || !soundEnabled}
          className="rounded-full p-1 text-primary-600 transition hover:bg-primary-50 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label={soundEnabled ? 'Hear coach message' : 'Coach sound disabled'}
          title={browserSpeech ? 'Hear coach message' : 'Browser speech is unavailable'}
        >
          {soundEnabled && browserSpeech ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
        </button>
      </div>
    </div>
  )
}

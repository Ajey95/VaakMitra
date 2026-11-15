import { useEffect, useState } from 'react'
import { Hand, RotateCcw, Volume2 } from 'lucide-react'
import { DEFAULT_AVATAR_PREFERENCE, normalizeAvatarPreference } from '../../features/avatar/avatarPreference'
import ExpressiveAvatar from '../avatar/ExpressiveAvatar'
import './InteractiveAvatar.css'

const PHASES = {
  IDLE: { label: 'Ready', mood: 'ready' },
  PROMPTING: { label: 'My turn', mood: 'speaking' },
  LISTENING: { label: 'Your turn', mood: 'listening' },
  PROCESSING: { label: 'Thinking', mood: 'thinking' },
  PRAISE: { label: 'Well done', mood: 'praise' },
  COACH: { label: 'Let’s practise', mood: 'coach' },
  RETRY: { label: 'Try the whole word', mood: 'retry' },
  BREAK: { label: 'Time for a break', mood: 'break' },
  ERROR: { label: 'Let’s record again', mood: 'error' },
}

export default function InteractiveAvatar({
  phase = 'IDLE',
  message = 'Ready when you are.',
  targetWord = '',
  speaking = false,
  audioLevel = 0,
  active = false,
  onStop,
  onReplay,
  scopeLabel = 'LOCAL PRACTICE',
  compact = false,
  avatarPreference = DEFAULT_AVATAR_PREFERENCE,
}) {
  const [viseme, setViseme] = useState(0)
  const current = PHASES[phase] || PHASES.ERROR
  const guide = normalizeAvatarPreference(avatarPreference)

  useEffect(() => {
    if (!speaking) { setViseme(0); return undefined }
    let next = 0
    const timer = window.setInterval(() => { next = (next + 1) % 4; setViseme(next) }, 120)
    return () => window.clearInterval(timer)
  }, [speaking])

  return <section className={`interactive-avatar interactive-avatar--${current.mood}${compact ? ' interactive-avatar--compact' : ''}`}
    aria-label="Interactive avatar coach" data-avatar-phase={phase}>
    <div className="interactive-avatar__scope">{scopeLabel}</div>
    <div className="interactive-avatar__bubble training-pippin__message" aria-live="polite">
      <strong>{current.label}</strong>
      <span>{message}</span>
      {targetWord ? <b lang="ta">{targetWord}</b> : null}
    </div>
    <div className="interactive-avatar__stage" data-viseme={viseme}>
      <ExpressiveAvatar avatarId={guide.avatarId} paletteId={guide.paletteId} motionLevel={guide.motionLevel}
        phase={phase} speaking={speaking} audioLevel={Math.max(audioLevel, speaking ? [0.2, 0.42, 0.82, 0.58][viseme] : 0)} />
      <span className="interactive-avatar__status">{current.label}</span>
      {phase === 'LISTENING' ? <span className="interactive-avatar__listening" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((bar) => <i key={bar} style={{ '--bar': bar, '--level': Math.max(0.15, audioLevel) }} />)}
      </span> : null}
    </div>
    <div className="interactive-avatar__actions">
      {onReplay ? <button type="button" className="interactive-avatar__replay" onClick={onReplay} disabled={phase === 'LISTENING' || phase === 'PROCESSING'}>
        {phase === 'ERROR' ? <RotateCcw aria-hidden="true" /> : <Volume2 aria-hidden="true" />} {phase === 'ERROR' ? 'Try recording again' : 'Hear again'}
      </button> : null}
      {active && onStop ? <button type="button" className="interactive-avatar__stop" onClick={onStop}>
        <Hand aria-hidden="true" /> Stop live practice
      </button> : null}
    </div>
  </section>
}

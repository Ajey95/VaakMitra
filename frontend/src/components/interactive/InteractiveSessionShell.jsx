import { useState } from 'react'
import { ArrowLeft, Pause, Play, Settings2, Waves } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useInteractionSettingsStore } from '../../store/interactionSettingsStore'
import SensorySettingsPanel from './SensorySettingsPanel'
import VisualSchedule from './VisualSchedule'
import ChildFeedback from './ChildFeedback'
import './play.css'

export default function InteractiveSessionShell({ title, subtitle, state, dispatch, steps, children, onExit, labels = {} }) {
  const navigate = useNavigate()
  const [showSettings, setShowSettings] = useState(false)
  const { preferences, setCalmMode } = useInteractionSettingsStore()
  const paused = state?.phase === 'paused'
  const activeIndex = Math.max(0, state?.stepIndex || 0)
  const ui = {
    playPractice: 'Play & Practice',
    exit: 'Exit activity',
    calm: 'Calm',
    settings: 'Comfort settings',
    resume: 'Resume activity',
    pause: 'Pause activity',
    ...labels,
  }

  const leave = () => (onExit ? onExit() : navigate('/play'))
  const togglePause = () => dispatch?.({ type: paused ? 'RESUME' : 'PAUSE', at: Date.now() })

  return (
    <main className="interactive-experience session-shell">
      <header className="session-shell__topbar">
        <button className="interactive-control session-shell__icon-button" type="button" onClick={leave} aria-label={ui.exit}>
          <ArrowLeft aria-hidden="true" />
        </button>
        <div className="session-shell__title">
          <span><Waves aria-hidden="true" /> {ui.playPractice}</span>
          <h1>{title}</h1>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        <div className="session-shell__actions">
          <button className={`interactive-control session-shell__calm ${preferences.calmMode ? 'is-active' : ''}`} type="button" onClick={() => setCalmMode(!preferences.calmMode)} aria-pressed={preferences.calmMode}>
            {ui.calm}
          </button>
          <button className="interactive-control session-shell__icon-button" type="button" onClick={() => setShowSettings(true)} aria-label={ui.settings}>
            <Settings2 aria-hidden="true" />
          </button>
          {dispatch ? (
            <button className="interactive-control session-shell__icon-button" type="button" onClick={togglePause} aria-label={paused ? ui.resume : ui.pause}>
              {paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}
            </button>
          ) : null}
        </div>
      </header>

      {steps?.length ? <VisualSchedule steps={steps} activeIndex={activeIndex} /> : null}

      <section className="session-shell__stage">
        {paused ? (
          <div className="session-shell__pause-card">
            <div className="session-shell__pause-orb" aria-hidden="true" />
            <ChildFeedback kind="paused" />
            <button className="interactive-control interactive-primary-button" type="button" onClick={togglePause}><Play aria-hidden="true" /> Keep playing</button>
          </div>
        ) : children}
      </section>

      {showSettings ? (
        <div className="session-shell__modal" role="dialog" aria-modal="true" aria-label={ui.settings}>
          <SensorySettingsPanel onDone={() => setShowSettings(false)} locale={ui.locale} />
        </div>
      ) : null}
    </main>
  )
}

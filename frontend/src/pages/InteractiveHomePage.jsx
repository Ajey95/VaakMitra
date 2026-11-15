import { useEffect } from 'react'
import { Camera, Gamepad2, Map, Mic, PawPrint, Settings2, Smile, Sparkles, Users } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import DashboardLayout from '../components/layout/DashboardLayout'
import { PLAY_DESTINATIONS } from '../features/interactive/activityCatalog'
import { useAuthStore } from '../store/authStore'
import { useInteractionSettingsStore } from '../store/interactionSettingsStore'
import '../components/interactive/play.css'

const ICONS = { balloon: Gamepad2, map: Map, smile: Smile, paw: PawPrint, users: Users, settings: Settings2 }

export default function InteractiveHomePage() {
  const navigate = useNavigate()
  const childAge = useAuthStore((state) => state.user?.child_age)
  const initialize = useInteractionSettingsStore((state) => state.initialize)

  useEffect(() => initialize({ age: childAge }), [childAge, initialize])

  return (
    <DashboardLayout title="Play & Practice" subtitle="Small adventures for brave communication" icon={Sparkles} maxWidth="max-w-6xl">
      <div className="interactive-experience play-home">
        <section className="play-home__welcome">
          <div>
            <span className="play-home__kicker"><Sparkles aria-hidden="true" /> Choose one adventure</span>
            <h2>What would you like to play?</h2>
            <p>Every try counts. You can pause, ask for help, or use a picture at any time.</p>
          </div>
          <div className="play-home__mascot" aria-hidden="true"><span>Hi!</span><PawPrint /></div>
        </section>

        <div className="play-home__grid">
          {PLAY_DESTINATIONS.map((item, index) => {
            const Icon = ICONS[item.icon]
            const CapabilityIcon = item.capability === 'microphone' ? Mic : item.capability === 'camera' ? Camera : null
            return (
              <button
                key={item.id}
                className={`interactive-control play-card play-card--${item.accent} ${index === 0 ? 'play-card--featured' : ''}`}
                type="button"
                onClick={() => navigate(item.path)}
              >
                <span className="play-card__icon"><Icon aria-hidden="true" /></span>
                <span className="play-card__body">
                  <span className="play-card__eyebrow">{item.eyebrow}</span>
                  <strong>{item.title}</strong>
                  <span>{item.description}</span>
                </span>
                {CapabilityIcon ? <span className="play-card__capability"><CapabilityIcon aria-hidden="true" /> {item.capability}</span> : null}
                <span className="play-card__arrow" aria-hidden="true">Go</span>
              </button>
            )
          })}
        </div>
      </div>
    </DashboardLayout>
  )
}

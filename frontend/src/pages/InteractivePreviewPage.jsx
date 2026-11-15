import { useReducer } from 'react'
import { useLocation } from 'react-router-dom'
import InteractiveSessionShell from '../components/interactive/InteractiveSessionShell'
import ChildFeedback from '../components/interactive/ChildFeedback'
import { createSession, sessionReducer } from '../features/interactive/sessionEngine'
import { PLAY_DESTINATIONS } from '../features/interactive/activityCatalog'

const previewSteps = [
  { id: 'hello', shortLabel: 'Hello' },
  { id: 'try', shortLabel: 'Try' },
  { id: 'play', shortLabel: 'Play' },
  { id: 'finish', shortLabel: 'Finish' },
]

export default function InteractivePreviewPage() {
  const location = useLocation()
  const activity = PLAY_DESTINATIONS.find((item) => item.path === location.pathname) || PLAY_DESTINATIONS[0]
  const [state, dispatch] = useReducer(sessionReducer, {
    ...createSession({ id: activity.id, steps: previewSteps }),
    phase: 'ready',
  })
  return (
    <InteractiveSessionShell title={activity.title} subtitle="Your activity is getting ready" state={state} dispatch={dispatch} steps={previewSteps}>
      <div className="session-preview-card">
        <span className="session-preview-card__orb" aria-hidden="true">{activity.title.slice(0, 1)}</span>
        <ChildFeedback title="Ready to play" detail="The full activity appears here in the next feature step." />
      </div>
    </InteractiveSessionShell>
  )
}

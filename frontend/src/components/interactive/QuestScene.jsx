import { Sparkles } from 'lucide-react'
import CharacterStage3D from './CharacterStage3D'

export default function QuestScene({
  stepId,
  chosenPath,
  bridgeProgress = 0,
  message,
  characterMood = 'idle',
  characterAudioLevel = 0,
  motionLevel = 'full',
  forceFallback = false,
  children,
}) {
  return (
    <div className={`quest-scene quest-scene--${stepId} ${chosenPath ? `quest-scene--${chosenPath}` : ''}`}>
      <img src="/assets/interactive/river-rescue/river-rescue-world.png" alt="Kavi the friendly elephant waiting beside a turquoise river and forest bridge" />
      <div className="quest-scene__wash" />
      <div className="quest-scene__story-chip"><Sparkles aria-hidden="true" /> River Rescue</div>
      {message ? <div className="quest-scene__speech" role="status" aria-live="polite">{message}</div> : null}
      <CharacterStage3D
        character="kavi"
        mood={characterMood}
        message={message}
        audioLevel={characterAudioLevel}
        motionLevel={motionLevel}
        forceFallback={forceFallback}
        className="quest-scene__kavi"
      />
      {stepId === 'lower-bridge' ? (
        <div className="quest-scene__bridge-progress" aria-label={`Bridge lowered ${Math.round(bridgeProgress * 100)} percent`}>
          <span style={{ width: `${Math.min(1, bridgeProgress) * 100}%` }} />
        </div>
      ) : null}
      <div className="quest-scene__controls">{children}</div>
    </div>
  )
}

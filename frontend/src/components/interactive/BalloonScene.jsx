import { Wind } from 'lucide-react'
import { AmbientEffects, CelebrationLayer } from './SceneEffects'

export default function BalloonScene({
  level,
  target = [0.25, 0.7],
  active,
  score,
  obstacles = [],
  crossedIds = [],
  lastCrossed = null,
  visualState = 'idle',
  motionLevel = 'full',
  effectProfile = { ambient: true, particles: 0, travel: false, durationMs: 0 },
  showMeter = true,
}) {
  const [minimum, maximum] = target
  const inZone = level >= minimum && level <= maximum
  const lift = Math.round(Math.min(1, level) * 185)
  const completed = crossedIds instanceof Set ? crossedIds : new Set(crossedIds)
  return (
    <div
      className={`balloon-scene ${active ? 'is-active' : ''} ${inZone ? 'is-in-zone' : ''}`}
      data-visual-state={visualState}
      data-motion={motionLevel}
    >
      <div className="balloon-scene__sky" aria-hidden="true">
        <AmbientEffects variant="meadow" enabled={effectProfile.ambient} />
        <span className="balloon-scene__cloud balloon-scene__cloud--one" />
        <span className="balloon-scene__cloud balloon-scene__cloud--two" />
        <div className="balloon-letter-path">
          {obstacles.map((obstacle) => (
            <span
              key={obstacle.id}
              data-testid="letter-obstacle"
              data-crossed={completed.has(obstacle.id) ? 'true' : 'false'}
              className="balloon-letter-obstacle"
              style={{ bottom: `${86 + obstacle.threshold * 185}px` }}
              aria-label={`Letter ${obstacle.letter}`}
            >
              {obstacle.letter}
            </span>
          ))}
        </div>
        <div className="balloon-scene__balloon" style={{ transform: `translateY(${-lift}px)` }}>
          <span className="balloon-scene__shine" />
          <span className="balloon-face">
            <i className="balloon-eye" /><i className="balloon-eye" /><i className="balloon-mouth" />
          </span>
          <span className="balloon-arm balloon-arm--left" />
          <span className="balloon-arm balloon-arm--right" />
          <span className="balloon-scene__knot" />
          <span className="balloon-scene__string" />
        </div>
        {visualState === 'complete' ? (
          <div className="balloon-flight-reward">
            <i className="balloon-rainbow" />
            <i className="balloon-treasure"><span>★</span></i>
          </div>
        ) : null}
        <CelebrationLayer variant="stars" state={visualState} effectProfile={effectProfile} />
        <span className="balloon-scene__ground" />
      </div>
      {showMeter ? (
        <>
          <div className="balloon-letter-announcement" aria-live="polite">
            {lastCrossed ? <><strong>{lastCrossed.letter}</strong> says {lastCrossed.sound}</> : 'Float through each letter to hear its sound'}
          </div>
          <div className="balloon-meter" aria-label={`Voice level ${Math.round(level * 100)} percent`}>
            <div className="balloon-meter__labels"><span>Soft</span><strong><Wind aria-hidden="true" /> Steady zone</strong><span>Strong</span></div>
            <div className="balloon-meter__track">
              <span className="balloon-meter__zone" style={{ left: `${minimum * 100}%`, width: `${(maximum - minimum) * 100}%` }} />
              <span className="balloon-meter__level" style={{ width: `${Math.min(1, level) * 100}%` }} />
            </div>
          </div>
        </>
      ) : null}
      {Number.isFinite(score) ? <div className="balloon-scene__score">Steady control <strong>{score}%</strong></div> : null}
    </div>
  )
}

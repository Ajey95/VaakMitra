export default function MouthGuideOverlay({ target, matched = false, progress = 0, visualState = 'model', motionLevel = 'full' }) {
  return (
    <div className={`mouth-guide ${matched ? 'is-matched' : ''}`} data-visual-state={visualState} data-motion={motionLevel}>
      <div className="mouth-guide__shine" aria-hidden="true"><i /><i /><i /></div>
      <div className="mouth-guide__visuals">
        <img src="/assets/interactive/mouth-mirror/mouth-mirror-therapist.png" alt="Friendly speech therapist showing the mouth movement" />
        <div className="mouth-guide__face" aria-hidden="true">
          <span className="mouth-guide__eye mouth-guide__eye--left" />
          <span className="mouth-guide__eye mouth-guide__eye--right" />
          <span className={`mouth-guide__mouth mouth-guide__mouth--${target.model}`} />
        </div>
      </div>
      <div className="mouth-guide__copy">
        <span>Make this shape</span>
        <strong>{target.sound}</strong>
        <p>{matched ? 'சரியாக செய்தாய்!' : target.cue}</p>
      </div>
      <div className="mouth-guide__hold" aria-label={`Hold progress ${Math.round(progress * 100)} percent`}>
        <span style={{ width: `${Math.min(1, progress) * 100}%` }} />
      </div>
    </div>
  )
}

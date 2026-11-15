import './scene-effects.css'

export function AmbientEffects({ variant, enabled = true }) {
  if (!enabled) return null
  return (
    <div className="scene-ambient" data-variant={variant} aria-hidden="true">
      <i /><i /><i /><i /><i /><i />
    </div>
  )
}

export function CelebrationLayer({ variant, state, effectProfile }) {
  const count = Math.max(0, Math.min(24, effectProfile?.particles || 0))
  if (!count) return null
  return (
    <div
      className="scene-celebration"
      data-variant={variant}
      data-state={state}
      data-travel={String(Boolean(effectProfile?.travel))}
      style={{ '--effect-duration': `${effectProfile?.durationMs || 0}ms` }}
      aria-hidden="true"
    >
      {Array.from({ length: count }, (_, index) => (
        <i className="scene-particle" key={index} style={{ '--particle-index': index }} />
      ))}
    </div>
  )
}

export function TamilStatus({ label }) {
  if (!label) return null
  return <span className="scene-status" role="status" aria-live="polite">{label}</span>
}

function distance(a, b) {
  if (!a || !b || ![a.x, a.y, b.x, b.y].every(Number.isFinite)) return null
  return Math.hypot(b.x - a.x, b.y - a.y)
}

function rounded(value) {
  return Math.round(value * 10_000) / 10_000
}

export function measureMouthGeometry(landmarks) {
  if (!Array.isArray(landmarks) || !landmarks[61] || !landmarks[291] || !landmarks[13] || !landmarks[14]) return null
  const width = distance(landmarks[61], landmarks[291])
  const height = distance(landmarks[13], landmarks[14])
  if (!width || height === null) return null
  return {
    mouthWidth: rounded(width),
    mouthHeight: rounded(height),
    mouthOpenRatio: rounded(height / width),
  }
}

export function classifyMouthTarget(geometry, target) {
  if (!geometry || !target) return { matched: false, cue: target?.cue || 'Move into the guide' }
  const matched = geometry.mouthOpenRatio >= target.minOpen
    && geometry.mouthOpenRatio <= target.maxOpen
    && (target.minWidth === undefined || geometry.mouthWidth >= target.minWidth)
    && (target.maxWidth === undefined || geometry.mouthWidth <= target.maxWidth)
  return { matched, cue: matched ? 'Hold it' : target.cue }
}

export function createHoldTracker(requiredMs = 600) {
  let heldMs = 0
  return {
    update(matched, deltaMs) {
      heldMs = matched ? Math.min(requiredMs, heldMs + Math.max(0, Number(deltaMs) || 0)) : 0
      return { heldMs, progress: heldMs / requiredMs, complete: heldMs >= requiredMs }
    },
    reset() { heldMs = 0 },
  }
}

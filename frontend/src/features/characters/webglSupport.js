export function supportsWebGL({
  documentRef = typeof document === 'undefined' ? null : document,
  forceFallback = false,
} = {}) {
  if (forceFallback || !documentRef?.createElement) return false
  try {
    const canvas = documentRef.createElement('canvas')
    return Boolean(canvas?.getContext?.('webgl2') || canvas?.getContext?.('webgl'))
  } catch {
    return false
  }
}

export function resolveApiBaseUrl({ isDevelopment, configuredUrl }) {
  if (isDevelopment) return '/api'
  const normalized = String(configuredUrl || '').trim()
  return normalized || '/api'
}

// Canonical routes include /api in their path; the inherited client already adds it.
export function resolveCanonicalApiBaseUrl(config) {
  return resolveApiBaseUrl(config).replace(/\/api\/?$/, '')
}

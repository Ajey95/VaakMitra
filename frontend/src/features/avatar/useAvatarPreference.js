import { useEffect, useState } from 'react'
import { avatarPreferenceKey, loadAvatarPreference } from './avatarPreference'

/** DEC-026/AVT-002: observe the child-scoped local preference across open views. */
export function useAvatarPreference(childId) {
  const storage = typeof window === 'undefined' ? null : window.localStorage
  const [preference, setPreference] = useState(() => loadAvatarPreference(storage, childId))

  useEffect(() => {
    setPreference(loadAvatarPreference(storage, childId))
    const key = avatarPreferenceKey(childId)
    const onStorage = (event) => {
      if (!event.key || event.key === key) setPreference(loadAvatarPreference(storage, childId))
    }
    const onPreference = (event) => {
      if (String(event.detail?.childId ?? '') === String(childId ?? '')) setPreference(loadAvatarPreference(storage, childId))
    }
    window.addEventListener('storage', onStorage)
    window.addEventListener('vaakmitra:avatar-preference', onPreference)
    return () => {
      window.removeEventListener('storage', onStorage)
      window.removeEventListener('vaakmitra:avatar-preference', onPreference)
    }
  }, [childId, storage])

  return preference
}

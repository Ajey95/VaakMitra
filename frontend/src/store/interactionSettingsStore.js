import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  DEFAULT_INTERACTION_PREFERENCES,
  applyCalmMode,
  migrateInteractionPreferences,
  resolveInitialPreferences,
} from '../features/interactive/preferences'

export const INTERACTION_STORAGE_KEY = 'speakeasy-interaction-preferences-v1'

function applyPreferenceAttributes(preferences) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.dataset.interactionMotion = preferences.motionLevel
  root.dataset.interactionContrast = preferences.contrastMode
  root.dataset.interactionAge = preferences.ageBand
}

export const useInteractionSettingsStore = create(
  persist(
    (set, get) => ({
      preferences: { ...DEFAULT_INTERACTION_PREFERENCES },
      initialized: false,
      initialize: ({ age } = {}) => {
        if (get().initialized) return
        const prefersReducedMotion = typeof window !== 'undefined'
          && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
        const hasPersistedChoice = typeof window !== 'undefined'
          && Boolean(window.localStorage.getItem(INTERACTION_STORAGE_KEY))
        const preferences = resolveInitialPreferences({
          saved: hasPersistedChoice ? get().preferences : undefined,
          age,
          prefersReducedMotion,
        })
        applyPreferenceAttributes(preferences)
        set({ preferences, initialized: true })
      },
      updatePreference: (key, value) => {
        const preferences = migrateInteractionPreferences({ ...get().preferences, [key]: value, calmMode: false })
        applyPreferenceAttributes(preferences)
        set({ preferences })
      },
      setCalmMode: (enabled) => {
        const preferences = applyCalmMode(get().preferences, enabled)
        applyPreferenceAttributes(preferences)
        set({ preferences })
      },
      resetPreferences: ({ age } = {}) => {
        const preferences = resolveInitialPreferences({ age })
        applyPreferenceAttributes(preferences)
        set({ preferences })
      },
    }),
    {
      name: INTERACTION_STORAGE_KEY,
      version: 1,
      partialize: (state) => ({ preferences: migrateInteractionPreferences(state.preferences) }),
      merge: (persisted, current) => ({
        ...current,
        preferences: migrateInteractionPreferences(persisted?.preferences),
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.preferences) applyPreferenceAttributes(state.preferences)
      },
    },
  ),
)

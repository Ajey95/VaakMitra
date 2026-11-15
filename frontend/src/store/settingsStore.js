import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Applies/removes the `dark` class on <html> so Tailwind's class dark mode kicks in.
const applyTheme = (darkMode) => {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  if (darkMode) root.classList.add('dark')
  else root.classList.remove('dark')
}

export const useSettingsStore = create(
  persist(
    (set, get) => ({
      darkMode: false,
      soundEnabled: true,
      notificationsEnabled: true,
      autoPlay: true,

      toggleDarkMode: () => {
        const next = !get().darkMode
        applyTheme(next)
        set({ darkMode: next })
      },
      setDarkMode: (value) => {
        applyTheme(value)
        set({ darkMode: value })
      },
      setSoundEnabled: (value) => set({ soundEnabled: value }),
      setNotificationsEnabled: (value) => set({ notificationsEnabled: value }),
      setAutoPlay: (value) => set({ autoPlay: value }),

      // Re-apply persisted theme to the DOM on app start
      initTheme: () => applyTheme(get().darkMode),
    }),
    {
      name: 'speakeasy-settings',
    }
  )
)

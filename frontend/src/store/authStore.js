import { create } from 'zustand'

// Browser sessions use an HttpOnly cookie. Tokens are never persisted in
// localStorage; the in-memory value only supports the Android bearer flow.
export const useAuthStore = create((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  authReady: false,
  setAuth: (user, token = null) => set({ user, token, isAuthenticated: true, authReady: true }),
  setUser: (user) => set({ user, isAuthenticated: Boolean(user), authReady: true }),
  markAuthReady: () => set({ authReady: true }),
  logout: () => set({ user: null, token: null, isAuthenticated: false, authReady: true }),
  updateUserStats: (stats) => set((state) => ({
    user: state.user ? { ...state.user, ...stats } : null,
  })),
}))

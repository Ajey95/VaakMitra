import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Home, GraduationCap, BookOpen, Video, Mic, ScanFace, ClipboardCheck,
  Gamepad2, BarChart3, FileText, Trophy, Gift, Calendar, Bell, Users,
  Stethoscope, CalendarClock, User, Settings, HelpCircle, MessageSquarePlus,
  Info, LogOut, Search, Moon, Sun, Menu, X, Star, ChevronLeft, Sparkles,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useSettingsStore } from '../../store/settingsStore'
import { authAPI } from '../../services/api'
import toast from 'react-hot-toast'

// Grouped navigation — the full information architecture of the platform
export const NAV_GROUPS = [
  {
    title: 'Overview',
    items: [
      { icon: Home, label: 'Dashboard', path: '/dashboard' },
      { icon: GraduationCap, label: 'Training', path: '/training' },
      { icon: Sparkles, label: 'Play & Practice', path: '/play' },
      { icon: ClipboardCheck, label: 'Assessment', path: '/assessment' },
    ],
  },
  {
    title: 'Learning',
    items: [
      { icon: BookOpen, label: 'Letter Learning', path: '/letter-learning' },
      { icon: Video, label: 'Training Videos', path: '/videos' },
      { icon: Mic, label: 'Speech Analysis', path: '/speech-analysis' },
      { icon: ScanFace, label: 'Tongue Tracking', path: '/tongue-tracking' },
      { icon: Gamepad2, label: 'Games', path: '/games' },
    ],
  },
  {
    title: 'Insights',
    items: [
      { icon: BarChart3, label: 'Progress', path: '/progress' },
      { icon: FileText, label: 'Reports', path: '/reports' },
      { icon: Trophy, label: 'Achievements', path: '/achievements' },
      { icon: Gift, label: 'Rewards', path: '/rewards' },
    ],
  },
  {
    title: 'Community',
    items: [
      { icon: Calendar, label: 'Calendar', path: '/calendar' },
      { icon: Bell, label: 'Notifications', path: '/notifications' },
      { icon: Users, label: 'Parent Hub', path: '/parent' },
      { icon: Stethoscope, label: 'Therapist Hub', path: '/therapist' },
      { icon: CalendarClock, label: 'Appointments', path: '/appointments' },
    ],
  },
  {
    title: 'Account',
    items: [
      { icon: User, label: 'Profile', path: '/profile' },
      { icon: Settings, label: 'Settings', path: '/settings' },
      { icon: HelpCircle, label: 'Help & Support', path: '/help' },
      { icon: MessageSquarePlus, label: 'Feedback', path: '/feedback' },
      { icon: Info, label: 'About', path: '/about' },
    ],
  },
]

const ALL_ITEMS = NAV_GROUPS.flatMap((g) => g.items)

function SidebarContent({ onNavigate, onClose }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()

  const go = (path) => {
    navigate(path)
    onNavigate?.()
  }

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="p-5 border-b border-neutral-100 dark:border-neutral-800 flex items-center justify-between">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => go('/')}>
          <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-secondary-500 rounded-xl flex items-center justify-center shadow-md shadow-primary-500/30">
            <span className="text-white font-bold text-sm">SE</span>
          </div>
          <div>
            <div className="font-bold text-neutral-900 dark:text-white text-sm">SpeakEasy ASD</div>
            <div className="text-[10px] text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Speech Therapy</div>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="lg:hidden p-2 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* User card */}
      <div className="px-4 pt-4">
        <div className="bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-primary-900/20 dark:to-secondary-900/20 rounded-2xl p-4 flex items-center gap-3 border border-primary-100 dark:border-primary-800/40">
          <div className="w-11 h-11 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-md rotate-3 shrink-0">
            {user?.child_name?.charAt(0) || user?.full_name?.charAt(0) || 'U'}
          </div>
          <div className="min-w-0">
            <h3 className="font-bold text-neutral-900 dark:text-white text-sm truncate">{user?.child_name || user?.full_name || 'Guest'}</h3>
            <div className="flex items-center gap-1 mt-0.5">
              <Star className="w-3.5 h-3.5 text-gold-500 fill-gold-500" />
              <span className="text-xs font-bold text-gold-600">{user?.total_stars || 0} Stars</span>
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5 scrollbar-thin">
        {NAV_GROUPS.map((group) => (
          <div key={group.title}>
            <div className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-neutral-400 dark:text-neutral-600">{group.title}</div>
            <div className="space-y-0.5">
              {group.items.map((link) => {
                const active = location.pathname === link.path || (link.path === '/play' && location.pathname.startsWith('/play/'))
                return (
                  <button
                    key={link.path}
                    onClick={() => go(link.path)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-all group ${
                      active
                        ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-lg shadow-primary-500/25'
                        : 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800'
                    }`}
                  >
                    <link.icon className={`w-[18px] h-[18px] shrink-0 ${active ? '' : 'group-hover:scale-110 transition-transform'}`} />
                    <span className="truncate">{link.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </nav>
    </div>
  )
}

/**
 * DashboardLayout — shared shell for every authenticated page.
 * Props:
 *   title, subtitle  — header text (rendered in the gradient banner)
 *   icon             — lucide icon component for the header
 *   actions          — optional React node rendered on the right of the header
 *   children         — page content
 *   maxWidth         — tailwind max-w utility (default max-w-7xl)
 */
export default function DashboardLayout({ title, subtitle, icon: Icon, actions, children, maxWidth = 'max-w-7xl' }) {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { darkMode, toggleDarkMode } = useSettingsStore()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [showResults, setShowResults] = useState(false)

  const results = useMemo(() => {
    if (!search.trim()) return []
    const q = search.toLowerCase()
    return ALL_ITEMS.filter((i) => i.label.toLowerCase().includes(q)).slice(0, 6)
  }, [search])

  const handleLogout = async () => {
    try { await authAPI.logout() } catch { /* ignore */ }
    logout()
    navigate('/')
    toast.success('Logged out successfully')
  }

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 transition-colors">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex fixed left-0 top-0 bottom-0 w-64 bg-white dark:bg-neutral-900 border-r border-neutral-100 dark:border-neutral-800 z-40 flex-col">
        <SidebarContent />
        <div className="p-3 border-t border-neutral-100 dark:border-neutral-800">
          <button onClick={handleLogout} className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl hover:bg-red-100 dark:hover:bg-red-900/30 transition font-medium text-sm">
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              className="lg:hidden fixed inset-0 bg-neutral-900/50 backdrop-blur-sm z-40"
            />
            <motion.aside
              initial={{ x: -300 }} animate={{ x: 0 }} exit={{ x: -300 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="lg:hidden fixed left-0 top-0 bottom-0 w-64 bg-white dark:bg-neutral-900 border-r border-neutral-100 dark:border-neutral-800 z-50 flex flex-col"
            >
              <SidebarContent onNavigate={() => setMobileOpen(false)} onClose={() => setMobileOpen(false)} />
              <div className="p-3 border-t border-neutral-100 dark:border-neutral-800">
                <button onClick={handleLogout} className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl font-medium text-sm">
                  <LogOut className="w-4 h-4" /> Sign Out
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main column */}
      <div className="lg:ml-64 min-h-screen flex flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-lg border-b border-neutral-100 dark:border-neutral-800">
          <div className="flex items-center gap-3 px-4 sm:px-6 h-16">
            <button onClick={() => setMobileOpen(true)} className="lg:hidden p-2 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg">
              <Menu className="w-5 h-5" />
            </button>

            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
              <input
                value={search}
                onChange={(e) => { setSearch(e.target.value); setShowResults(true) }}
                onFocus={() => setShowResults(true)}
                onBlur={() => setTimeout(() => setShowResults(false), 150)}
                placeholder="Search pages, lessons, reports…"
                className="w-full pl-10 pr-4 py-2 bg-neutral-100 dark:bg-neutral-800 rounded-xl text-sm text-neutral-700 dark:text-neutral-200 placeholder:text-neutral-400 border border-transparent focus:border-primary-300 focus:bg-white dark:focus:bg-neutral-900 outline-none transition"
              />
              <AnimatePresence>
                {showResults && results.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}
                    className="absolute top-full mt-2 left-0 right-0 bg-white dark:bg-neutral-900 rounded-2xl shadow-premium border border-neutral-100 dark:border-neutral-800 p-2 z-50"
                  >
                    {results.map((r) => (
                      <button
                        key={r.path}
                        onMouseDown={() => { navigate(r.path); setSearch('') }}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
                      >
                        <r.icon className="w-4 h-4 text-primary-500" />
                        {r.label}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="flex items-center gap-1.5 ml-auto">
              <button onClick={toggleDarkMode} className="p-2.5 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-xl transition" title="Toggle theme">
                {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
              <button onClick={() => navigate('/notifications')} className="relative p-2.5 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-xl transition" title="Notifications">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-coral-500 rounded-full ring-2 ring-white dark:ring-neutral-900" />
              </button>
              <button onClick={() => navigate('/profile')} className="flex items-center gap-2 pl-1.5 pr-3 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-xl transition">
                <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-sm">
                  {user?.child_name?.charAt(0) || user?.full_name?.charAt(0) || 'U'}
                </div>
                <span className="hidden sm:block text-sm font-semibold text-neutral-700 dark:text-neutral-200 max-w-[120px] truncate">{user?.child_name || user?.full_name || 'Guest'}</span>
              </button>
            </div>
          </div>
        </header>

        {/* Page header banner */}
        {(title || actions) && (
          <div className="bg-gradient-to-r from-primary-600 via-primary-700 to-secondary-700 text-white px-4 sm:px-8 py-7 relative overflow-hidden">
            <div className="absolute inset-0 bg-grid opacity-5" />
            <div className="absolute -right-10 -top-10 w-48 h-48 bg-white/10 rounded-full blur-3xl" />
            <div className={`${maxWidth} mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10`}>
              <div className="flex items-center gap-4">
                {Icon && (
                  <div className="w-12 h-12 bg-white/15 backdrop-blur rounded-2xl flex items-center justify-center shrink-0">
                    <Icon className="w-6 h-6" />
                  </div>
                )}
                <div>
                  <h1 className="text-2xl sm:text-3xl font-bold">{title}</h1>
                  {subtitle && <p className="text-white/70 text-sm mt-1">{subtitle}</p>}
                </div>
              </div>
              {actions && <div className="flex items-center gap-2">{actions}</div>}
            </div>
          </div>
        )}

        {/* Content */}
        <main className="flex-1 px-4 sm:px-8 py-8">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className={`${maxWidth} mx-auto`}
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  )
}

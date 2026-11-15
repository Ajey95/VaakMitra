import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, User, Bell, Shield, Volume2, HelpCircle, Moon, Globe, Palette, Heart, X, Lock, Eye, EyeOff, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useSettingsStore } from '../store/settingsStore'
import { authAPI } from '../services/api'
import toast from 'react-hot-toast'

function SettingToggle({ label, description, checked, onChange, icon: Icon, iconColor = 'text-primary-600' }) {
  return (
    <div className="flex items-center justify-between p-5 bg-neutral-50 dark:bg-neutral-800 rounded-2xl border border-neutral-100 dark:border-neutral-700 hover:border-primary-200 dark:hover:border-primary-500/50 transition-all">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 bg-white dark:bg-neutral-900 rounded-xl flex items-center justify-center shadow-sm border border-neutral-100 dark:border-neutral-700">
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
        <div>
          <div className="font-semibold text-neutral-800 dark:text-neutral-100 text-sm">{label}</div>
          <div className="text-xs text-neutral-500 dark:text-neutral-400">{description}</div>
        </div>
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input type="checkbox" checked={checked} onChange={onChange} className="sr-only peer" />
        <div className="w-12 h-6 bg-neutral-300 dark:bg-neutral-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-100 dark:peer-focus:ring-primary-900 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all after:shadow-sm peer-checked:bg-gradient-to-r peer-checked:from-primary-500 peer-checked:to-secondary-500" />
      </label>
    </div>
  )
}

function SettingSection({ title, icon: Icon, children, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-white dark:bg-neutral-900 rounded-3xl shadow-md p-8 border border-neutral-100 dark:border-neutral-800 transition-colors"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-primary-50 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
          <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-xl font-bold text-neutral-900 dark:text-white">{title}</h2>
      </div>
      {children}
    </motion.div>
  )
}

function PasswordField({ label, value, onChange, show, onToggle, placeholder }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 mb-1.5 uppercase tracking-wider">{label}</label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="w-full px-4 py-3 pr-11 bg-neutral-50 dark:bg-neutral-800 rounded-xl text-neutral-800 dark:text-neutral-100 border border-neutral-200 dark:border-neutral-700 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 dark:focus:ring-primary-900 outline-none text-sm transition"
        />
        <button type="button" onClick={onToggle} className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200">
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  )
}

function ChangePasswordModal({ onClose }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState({ current: false, next: false, confirm: false })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (next.length < 6) return toast.error('New password must be at least 6 characters')
    if (next !== confirm) return toast.error('New passwords do not match')
    if (next === current) return toast.error('New password must be different')

    setLoading(true)
    try {
      await authAPI.changePassword({ current_password: current, new_password: next })
      toast.success('Password changed successfully!')
      onClose()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not change password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.92, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white dark:bg-neutral-900 rounded-3xl shadow-premium-lg p-8 max-w-md w-full"
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-50 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
              <Lock className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <h3 className="text-xl font-bold text-neutral-900 dark:text-white">Change Password</h3>
          </div>
          <button onClick={onClose} className="p-2 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <PasswordField label="Current Password" value={current} placeholder="Enter current password"
            onChange={(e) => setCurrent(e.target.value)} show={show.current} onToggle={() => setShow(s => ({ ...s, current: !s.current }))} />
          <PasswordField label="New Password" value={next} placeholder="At least 6 characters"
            onChange={(e) => setNext(e.target.value)} show={show.next} onToggle={() => setShow(s => ({ ...s, next: !s.next }))} />
          <PasswordField label="Confirm New Password" value={confirm} placeholder="Re-enter new password"
            onChange={(e) => setConfirm(e.target.value)} show={show.confirm} onToggle={() => setShow(s => ({ ...s, confirm: !s.confirm }))} />

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-3 rounded-xl border-2 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 font-semibold hover:border-primary-300 transition">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-3 rounded-xl bg-gradient-to-r from-primary-500 to-secondary-500 text-white font-semibold transition disabled:opacity-60 inline-flex items-center justify-center gap-2">
              {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</> : 'Update Password'}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}

export default function SettingsPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const {
    darkMode, soundEnabled, notificationsEnabled, autoPlay,
    toggleDarkMode, setSoundEnabled, setNotificationsEnabled, setAutoPlay,
  } = useSettingsStore()
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const supportItems = [
    { title: 'How to Use SpeakEasy', desc: 'Step-by-step guide to get the most out of speech therapy sessions', icon: '📖', action: () => navigate('/help') },
    { title: 'Contact Support', desc: 'Get help from our team at speakeasy@amrita.edu', icon: '✉️', action: () => { window.location.href = 'mailto:speakeasy@amrita.edu' } },
    { title: 'About SpeakEasy ASD', desc: 'Version 1.0.0 — Team 96, Amrita Vishwa Vidyapeetham', icon: 'ℹ️', action: () => navigate('/about') },
    { title: 'Research & Privacy', desc: 'Learn about our privacy-first approach and research methodology', icon: '🔬', action: () => navigate('/about#privacy') },
  ]

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 transition-colors">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 via-primary-700 to-secondary-700 text-white py-8 px-8 shadow-xl relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-5" />
        <div className="max-w-4xl mx-auto flex items-center gap-4 relative z-10">
          <button onClick={() => navigate('/dashboard')} className="p-2.5 hover:bg-white/10 rounded-xl transition">
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-3xl font-bold">Settings</h1>
            <p className="text-white/70 text-sm mt-1">Manage your account preferences and application settings</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-8 space-y-6">
        {/* Profile */}
        <SettingSection title="Profile Information" icon={User} delay={0}>
          <div className="flex items-center gap-6 mb-6 p-5 bg-gradient-to-r from-primary-50 to-secondary-50 dark:from-primary-900/20 dark:to-secondary-900/20 rounded-2xl border border-primary-100 dark:border-primary-800/40">
            <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-2xl flex items-center justify-center text-white font-bold text-3xl shadow-lg rotate-3">
              {user?.child_name?.charAt(0) || 'U'}
            </div>
            <div>
              <h3 className="text-lg font-bold text-neutral-900 dark:text-white">{user?.child_name}</h3>
              <p className="text-sm text-neutral-600 dark:text-neutral-300">{user?.full_name}</p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">{user?.email}</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {[
              { label: 'Parent Name', value: user?.full_name },
              { label: 'Email', value: user?.email },
              { label: 'Child Name', value: user?.child_name },
              { label: 'Child Age', value: `${user?.child_age || '—'} years` },
            ].map((field, i) => (
              <div key={i}>
                <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 mb-1.5 uppercase tracking-wider">{field.label}</label>
                <div className="px-4 py-3 bg-neutral-50 dark:bg-neutral-800 rounded-xl text-neutral-700 dark:text-neutral-200 border border-neutral-100 dark:border-neutral-700 text-sm font-medium">
                  {field.value || '—'}
                </div>
              </div>
            ))}
          </div>
        </SettingSection>

        {/* Sound & Notifications */}
        <SettingSection title="Sound & Notifications" icon={Volume2} delay={0.1}>
          <div className="space-y-3">
            <SettingToggle
              icon={Volume2} iconColor="text-blue-600"
              label="Sound Effects"
              description="Play audio feedback during therapy sessions and celebrations"
              checked={soundEnabled}
              onChange={(e) => { setSoundEnabled(e.target.checked); toast.success(e.target.checked ? 'Sound enabled' : 'Sound disabled') }}
            />
            <SettingToggle
              icon={Bell} iconColor="text-amber-600"
              label="Practice Reminders"
              description="Get daily reminders to practice speech therapy exercises"
              checked={notificationsEnabled}
              onChange={(e) => { setNotificationsEnabled(e.target.checked); toast.success(e.target.checked ? 'Reminders enabled' : 'Reminders disabled') }}
            />
            <SettingToggle
              icon={Globe} iconColor="text-emerald-600"
              label="Auto-Play Pronunciation"
              description="Automatically play letter/word pronunciation when entering a lesson"
              checked={autoPlay}
              onChange={(e) => { setAutoPlay(e.target.checked); toast.success(e.target.checked ? 'Auto-play enabled' : 'Auto-play disabled') }}
            />
          </div>
        </SettingSection>

        {/* Appearance */}
        <SettingSection title="Appearance" icon={Palette} delay={0.2}>
          <div className="space-y-3">
            <SettingToggle
              icon={Moon} iconColor="text-violet-600"
              label="Dark Mode"
              description="Switch to a dark theme that's easier on the eyes"
              checked={darkMode}
              onChange={() => { toggleDarkMode(); toast.success(!darkMode ? 'Dark mode on 🌙' : 'Light mode on ☀️') }}
            />
          </div>
        </SettingSection>

        {/* Security */}
        <SettingSection title="Security" icon={Shield} delay={0.3}>
          <button
            onClick={() => setShowPasswordModal(true)}
            className="w-full px-6 py-4 border-2 border-primary-200 dark:border-primary-700 text-primary-700 dark:text-primary-300 rounded-2xl hover:bg-primary-50 dark:hover:bg-primary-900/20 transition font-semibold flex items-center justify-center gap-2"
          >
            <Shield className="w-5 h-5" />
            Change Password
          </button>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 text-center mt-3">Your password is encrypted with bcrypt (10 rounds) for maximum security</p>
        </SettingSection>

        {/* Help */}
        <SettingSection title="Help & Support" icon={HelpCircle} delay={0.4}>
          <div className="space-y-3">
            {supportItems.map((item, i) => (
              <button key={i}
                onClick={item.action}
                className="w-full text-left px-5 py-4 bg-neutral-50 dark:bg-neutral-800 hover:bg-primary-50 dark:hover:bg-neutral-700 rounded-2xl transition-all flex items-center gap-4 border border-neutral-100 dark:border-neutral-700 hover:border-primary-200 group"
              >
                <span className="text-2xl">{item.icon}</span>
                <div>
                  <div className="font-semibold text-neutral-800 dark:text-neutral-100 text-sm group-hover:text-primary-700 dark:group-hover:text-primary-300 transition-colors">{item.title}</div>
                  <div className="text-xs text-neutral-500 dark:text-neutral-400">{item.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </SettingSection>

        {/* Footer note */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-xs text-neutral-400 dark:text-neutral-500 pb-4 flex items-center justify-center gap-1"
        >
          Made with <Heart className="w-3 h-3 text-red-400 fill-red-400" /> by Team 96 — SpeakEasy ASD v1.0
        </motion.p>
      </div>

      <AnimatePresence>
        {showPasswordModal && <ChangePasswordModal onClose={() => setShowPasswordModal(false)} />}
      </AnimatePresence>
    </div>
  )
}

import { motion } from 'framer-motion'

/* ============================================================
   SHARED UI KIT — premium building blocks used across pages
   ============================================================ */

export function Card({ children, className = '', delay = 0, hover = false, ...rest }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      whileHover={hover ? { y: -4 } : undefined}
      className={`bg-white dark:bg-neutral-900 rounded-3xl shadow-md border border-neutral-100 dark:border-neutral-800 transition-colors ${className}`}
      {...rest}
    >
      {children}
    </motion.div>
  )
}

export function SectionTitle({ title, subtitle, icon: Icon, action }) {
  return (
    <div className="flex items-center justify-between mb-5">
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="w-10 h-10 bg-primary-50 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
            <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
        )}
        <div>
          <h2 className="text-xl font-bold text-neutral-900 dark:text-white">{title}</h2>
          {subtitle && <p className="text-sm text-neutral-500 dark:text-neutral-400">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  )
}

const GRADIENTS = {
  primary: 'from-primary-500 to-indigo-600',
  secondary: 'from-secondary-500 to-cyan-600',
  accent: 'from-accent-500 to-emerald-600',
  gold: 'from-gold-400 to-amber-500',
  coral: 'from-coral-500 to-rose-600',
}
const SOFT_BG = {
  primary: 'bg-indigo-50 dark:bg-neutral-900 border-indigo-100 dark:border-neutral-800',
  secondary: 'bg-cyan-50 dark:bg-neutral-900 border-cyan-100 dark:border-neutral-800',
  accent: 'bg-emerald-50 dark:bg-neutral-900 border-emerald-100 dark:border-neutral-800',
  gold: 'bg-amber-50 dark:bg-neutral-900 border-amber-100 dark:border-neutral-800',
  coral: 'bg-rose-50 dark:bg-neutral-900 border-rose-100 dark:border-neutral-800',
}

export function StatCard({ icon: Icon, title, value, sub, color = 'primary', delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      whileHover={{ y: -4 }}
      className={`rounded-2xl p-6 border hover:shadow-lg transition-all duration-300 ${SOFT_BG[color]}`}
    >
      <div className={`w-12 h-12 bg-gradient-to-br ${GRADIENTS[color]} rounded-xl flex items-center justify-center mb-4 shadow-md`}>
        {Icon && <Icon className="w-6 h-6 text-white" />}
      </div>
      <div className="text-3xl font-bold text-neutral-900 dark:text-white mb-1">{value}</div>
      <div className="text-sm text-neutral-500 dark:text-neutral-400">{title}</div>
      {sub && <div className="text-xs text-accent-600 dark:text-accent-400 font-semibold mt-1">{sub}</div>}
    </motion.div>
  )
}

/** Animated circular progress ring */
export function ProgressRing({ value = 0, size = 120, stroke = 10, color = '#4F46E5', label, sublabel }) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (Math.min(100, Math.max(0, value)) / 100) * circumference
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="currentColor" strokeWidth={stroke} fill="none" className="text-neutral-100 dark:text-neutral-800" />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-neutral-900 dark:text-white">{label ?? `${Math.round(value)}%`}</span>
        {sublabel && <span className="text-[10px] text-neutral-400 uppercase tracking-wide">{sublabel}</span>}
      </div>
    </div>
  )
}

export function Badge({ children, color = 'primary', className = '' }) {
  const styles = {
    primary: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300',
    accent: 'bg-accent-100 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300',
    gold: 'bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-300',
    coral: 'bg-coral-100 text-coral-700 dark:bg-coral-900/30 dark:text-coral-300',
    neutral: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300',
  }
  return <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${styles[color]} ${className}`}>{children}</span>
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      <div className="w-20 h-20 bg-neutral-100 dark:bg-neutral-800 rounded-3xl flex items-center justify-center mb-5">
        {Icon && <Icon className="w-9 h-9 text-neutral-400" />}
      </div>
      <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100 mb-1">{title}</h3>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 max-w-sm mb-5">{description}</p>
      {action}
    </div>
  )
}

export function GradientButton({ children, onClick, className = '', type = 'button', disabled }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary-500 to-secondary-500 text-white font-semibold text-sm shadow-md hover:shadow-lg shadow-primary-500/25 transition disabled:opacity-60 ${className}`}
    >
      {children}
    </button>
  )
}

import { useId, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  User, Camera, Mail, Phone, MapPin, Calendar, Baby, Heart, Globe,
  Shield, Lock, Bell, KeyRound, Trash2, Save, Pencil, X, AlertTriangle,
  Stethoscope, Activity, Pill, Users, Languages, Palette, ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import DashboardLayout from '../components/layout/DashboardLayout'
import AvatarPicker from '../components/avatar/AvatarPicker'
import { Card, SectionTitle, Badge, GradientButton } from '../components/ui'
import { loadAvatarPreference, saveAvatarPreference } from '../features/avatar/avatarPreference'
import { useAuthStore } from '../store/authStore'
import { privacyAPI, profileAPI } from '../services/api'

const TABS = [
  { id: 'personal', label: 'Personal Info', icon: User },
  { id: 'child', label: 'Child Information', icon: Baby },
  { id: 'medical', label: 'Medical Details', icon: Stethoscope },
  { id: 'emergency', label: 'Emergency Contact', icon: Phone },
  { id: 'preferences', label: 'Preferences', icon: Palette },
]

function Field({ label, icon: Icon, value, onChange, editing, type = 'text', placeholder }) {
  const fieldId = useId()
  return (
    <div>
      <label htmlFor={fieldId} className="flex items-center gap-1.5 text-xs font-semibold text-neutral-500 dark:text-neutral-400 mb-1.5 uppercase tracking-wide">
        {Icon && <Icon className="w-3.5 h-3.5" />} {label}
      </label>
      <input
        id={fieldId}
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={!editing}
        onChange={(e) => onChange?.(e.target.value)}
        className={`w-full px-4 py-2.5 rounded-xl text-sm border outline-none transition ${
          editing
            ? 'bg-white dark:bg-neutral-900 border-primary-300 dark:border-primary-700 text-neutral-800 dark:text-white focus:ring-2 focus:ring-primary-200'
            : 'bg-neutral-50 dark:bg-neutral-800/60 border-neutral-100 dark:border-neutral-800 text-neutral-600 dark:text-neutral-300 cursor-default'
        }`}
      />
    </div>
  )
}

function SelectField({ label, icon: Icon, value, onChange, editing, options }) {
  const fieldId = useId()
  return (
    <div>
      <label htmlFor={fieldId} className="flex items-center gap-1.5 text-xs font-semibold text-neutral-500 dark:text-neutral-400 mb-1.5 uppercase tracking-wide">
        {Icon && <Icon className="w-3.5 h-3.5" />} {label}
      </label>
      <select
        id={fieldId}
        value={value}
        disabled={!editing}
        onChange={(e) => onChange?.(e.target.value)}
        className={`w-full px-4 py-2.5 rounded-xl text-sm border outline-none transition ${
          editing
            ? 'bg-white dark:bg-neutral-900 border-primary-300 dark:border-primary-700 text-neutral-800 dark:text-white focus:ring-2 focus:ring-primary-200'
            : 'bg-neutral-50 dark:bg-neutral-800/60 border-neutral-100 dark:border-neutral-800 text-neutral-600 dark:text-neutral-300 cursor-default'
        }`}
      >
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )
}

export default function ProfilePage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [tab, setTab] = useState('personal')
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [confirmText, setConfirmText] = useState('')
  const [avatar, setAvatar] = useState('')
  const avatarInputRef = useRef(null)
  const avatarChildId = user?.child_id || user?.childId || user?.id || user?._id || ''
  const [practiceGuide, setPracticeGuide] = useState(() => loadAvatarPreference(typeof window === 'undefined' ? null : window.localStorage, avatarChildId))

  const name = user?.full_name || 'Priya Raman'

  const [form, setForm] = useState({
    full_name: user?.full_name || 'Priya Raman',
    email: user?.email || 'priya.raman@gmail.com',
    phone: '+91 98765 43210',
    location: 'Coimbatore, Tamil Nadu',
    dob: '1988-04-12',
    child_name: user?.child_name || 'Arjun',
    child_age: String(user?.child_age || 6),
    child_gender: 'Male',
    diagnosis: 'ASD Level 1',
    diagnosedAt: 'March 2022',
    therapist: 'Dr. Lakshmi Narayan',
    medications: 'None',
    allergies: 'None reported',
    emName: 'Ravi Raman',
    emRelation: 'Father',
    emPhone: '+91 98765 11111',
    emEmail: 'ravi.raman@gmail.com',
    language: 'Tamil',
    theme: 'System',
  })

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSave = async () => {
    try {
      if (tab === 'personal') {
        await profileAPI.updatePersonal({ full_name: form.full_name, phone: form.phone, city: form.location, dob: form.dob })
      } else if (tab === 'child') {
        await profileAPI.updateChild({ child_name: form.child_name, child_age: Number(form.child_age), child_gender: form.child_gender, language: form.language })
      } else if (tab === 'medical') {
        await profileAPI.updateMedical({ diagnosis: form.diagnosis, allergies: form.allergies, medications: form.medications, therapist_name: form.therapist })
      } else if (tab === 'emergency') {
        await profileAPI.addEmergency({ name: form.emName, relationship: form.emRelation, phone: form.emPhone, email: form.emEmail || null })
      } else {
        localStorage.setItem('speakeasy-profile-preferences', JSON.stringify({ language: form.language, theme: form.theme }))
      }
      setEditing(false)
      toast.success(tab === 'preferences' ? 'Preferences saved on this device' : 'Profile updated')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not save profile changes')
    }
  }

  const handleDelete = async () => {
    if (confirmText !== 'DELETE') {
      toast.error('Type DELETE to confirm')
      return
    }
    try {
      await privacyAPI.requestDeletion('Requested from profile settings')
      setShowDelete(false)
      setConfirmText('')
      toast.success('Account deletion request submitted')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not submit the deletion request')
    }
  }

  const handleAvatarChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      toast.error('Choose an image file')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Profile pictures must be smaller than 2 MB')
      return
    }
    const reader = new FileReader()
    reader.onload = async () => {
      setAvatar(String(reader.result || ''))
      try {
        await profileAPI.setAvatar(String(reader.result || ''))
        toast.success('Profile picture updated')
      } catch {
        toast.error('Picture preview updated, but it could not be saved to your account')
      }
    }
    reader.readAsDataURL(file)
  }

  const handlePracticeGuideSave = (next) => {
    const saved = saveAvatarPreference(window.localStorage, avatarChildId, next)
    setPracticeGuide(saved)
    window.dispatchEvent(new CustomEvent('vaakmitra:avatar-preference', { detail: { childId: avatarChildId, preference: saved } }))
    toast.success('Practice guide saved for this child')
  }

  return (
    <DashboardLayout title="My Profile" subtitle="Manage your account and child details" icon={User}>
      {/* Hero */}
      <Card className="overflow-hidden mb-6">
        <div className="h-28 bg-gradient-to-r from-primary-500 via-primary-600 to-secondary-500 relative">
          <div className="absolute inset-0 bg-grid opacity-10" />
        </div>
        <div className="px-6 pb-6 -mt-12 flex flex-col sm:flex-row sm:items-end gap-4">
          <div className="relative shrink-0">
            <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white text-4xl font-bold ring-4 ring-white dark:ring-neutral-900 shadow-lg overflow-hidden">
              {avatar ? (
                <img data-testid="profile-avatar-preview" src={avatar} alt={`${name} profile`} className="h-full w-full object-cover" />
              ) : name.charAt(0)}
            </div>
            <input
              ref={avatarInputRef}
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={handleAvatarChange}
            />
            <button
              type="button"
              aria-label="Upload profile picture"
              onClick={() => avatarInputRef.current?.click()}
              className="absolute -bottom-1 -right-1 w-9 h-9 bg-white dark:bg-neutral-800 rounded-full flex items-center justify-center shadow-md border border-neutral-100 dark:border-neutral-700 hover:scale-110 transition"
            >
              <Camera className="w-4 h-4 text-primary-600 dark:text-primary-400" />
            </button>
          </div>
          <div className="flex-1 sm:pb-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-2xl font-bold text-neutral-900 dark:text-white">{name}</h2>
              <Badge color="primary">Parent / Caregiver</Badge>
            </div>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1 flex items-center gap-2">
              <Mail className="w-3.5 h-3.5" /> {form.email}
            </p>
            <p className="text-xs text-neutral-400 mt-1 flex items-center gap-1.5">
              <Calendar className="w-3 h-3" /> Member since January 2024
            </p>
          </div>
          <div className="sm:pb-1">
            {editing ? (
              <div className="flex gap-2">
                <button onClick={() => setEditing(false)} className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 transition">
                  Cancel
                </button>
                <GradientButton onClick={handleSave}><Save className="w-4 h-4" /> Save</GradientButton>
              </div>
            ) : (
              <GradientButton onClick={() => setEditing(true)}><Pencil className="w-4 h-4" /> Edit Profile</GradientButton>
            )}
          </div>
        </div>
      </Card>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Tabs */}
        <div className="lg:col-span-1">
          <Card className="p-2">
            {TABS.map((t) => {
              const active = tab === t.id
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition mb-0.5 ${
                    active
                      ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-md'
                      : 'text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                  }`}
                >
                  <t.icon className="w-4 h-4" /> {t.label}
                </button>
              )
            })}
          </Card>

          {/* Privacy quick links */}
          <Card className="p-4 mt-6">
            <SectionTitle title="Privacy & Security" icon={Shield} />
            {[
              { icon: Lock, label: 'Change Password', path: '/settings' },
              { icon: KeyRound, label: 'Two-Factor Auth', status: 'Not configured' },
              { icon: Bell, label: 'Login Activity', status: 'Current session protected' },
            ].map((l) => (
              <button
                key={l.label}
                type="button"
                onClick={() => l.path && navigate(l.path)}
                disabled={!l.path}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition disabled:cursor-default disabled:opacity-70"
              >
                <span className="flex items-center gap-2.5"><l.icon className="w-4 h-4 text-primary-500" /> {l.label}</span>
                {l.path ? <ChevronRight className="w-4 h-4 text-neutral-300" /> : <span className="text-[10px] text-neutral-400">{l.status}</span>}
              </button>
            ))}
          </Card>
        </div>

        {/* Tab content */}
        <div className="lg:col-span-3">
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <Card className="p-6">
                {tab === 'personal' && (
                  <>
                    <SectionTitle title="Personal Information" subtitle="Your account details" icon={User} />
                    <div className="grid sm:grid-cols-2 gap-5">
                      <Field label="Full Name" icon={User} value={form.full_name} onChange={set('full_name')} editing={editing} />
                      <Field label="Email" icon={Mail} type="email" value={form.email} onChange={set('email')} editing={editing} />
                      <Field label="Phone" icon={Phone} value={form.phone} onChange={set('phone')} editing={editing} />
                      <Field label="Location" icon={MapPin} value={form.location} onChange={set('location')} editing={editing} />
                      <Field label="Date of Birth" icon={Calendar} type="date" value={form.dob} onChange={set('dob')} editing={editing} />
                    </div>
                  </>
                )}

                {tab === 'child' && (
                  <>
                    <SectionTitle title="Child Information" subtitle="Details about your child" icon={Baby} />
                    <div className="grid sm:grid-cols-2 gap-5">
                      <Field label="Child's Name" icon={Baby} value={form.child_name} onChange={set('child_name')} editing={editing} />
                      <Field label="Age" icon={Calendar} type="number" value={form.child_age} onChange={set('child_age')} editing={editing} />
                      <SelectField label="Gender" icon={User} value={form.child_gender} onChange={set('child_gender')} editing={editing} options={['Male', 'Female', 'Other']} />
                      <Field label="Native Language" icon={Languages} value={form.language} onChange={set('language')} editing={editing} />
                    </div>
                  </>
                )}

                {tab === 'medical' && (
                  <>
                    <SectionTitle title="Medical Details" subtitle="Clinical and therapy information" icon={Stethoscope} />
                    <div className="grid sm:grid-cols-2 gap-5">
                      <Field label="Diagnosis" icon={Activity} value={form.diagnosis} onChange={set('diagnosis')} editing={editing} />
                      <Field label="Diagnosed" icon={Calendar} value={form.diagnosedAt} onChange={set('diagnosedAt')} editing={editing} />
                      <Field label="Therapist" icon={Stethoscope} value={form.therapist} onChange={set('therapist')} editing={editing} />
                      <Field label="Medications" icon={Pill} value={form.medications} onChange={set('medications')} editing={editing} />
                      <Field label="Allergies" icon={Heart} value={form.allergies} onChange={set('allergies')} editing={editing} />
                    </div>
                  </>
                )}

                {tab === 'emergency' && (
                  <>
                    <SectionTitle title="Emergency Contact" subtitle="Who to reach in an emergency" icon={Phone} />
                    <div className="grid sm:grid-cols-2 gap-5">
                      <Field label="Contact Name" icon={User} value={form.emName} onChange={set('emName')} editing={editing} />
                      <Field label="Relationship" icon={Users} value={form.emRelation} onChange={set('emRelation')} editing={editing} />
                      <Field label="Phone" icon={Phone} value={form.emPhone} onChange={set('emPhone')} editing={editing} />
                      <Field label="Email" icon={Mail} type="email" value={form.emEmail} onChange={set('emEmail')} editing={editing} />
                    </div>
                  </>
                )}

                {tab === 'preferences' && (
                  <>
                    <SectionTitle title="Preferences" subtitle="Personalize your experience" icon={Palette} />
                    <div className="grid sm:grid-cols-2 gap-5">
                      <SelectField label="App Language" icon={Globe} value={form.language} onChange={set('language')} editing={editing} options={['Tamil', 'English', 'Hindi']} />
                      <SelectField label="Theme" icon={Palette} value={form.theme} onChange={set('theme')} editing={editing} options={['System', 'Light', 'Dark']} />
                    </div>
                    <div className="mt-5 p-4 rounded-2xl bg-primary-50 dark:bg-primary-900/20 border border-primary-100 dark:border-primary-800/40 text-sm text-primary-700 dark:text-primary-300 flex items-start gap-3">
                      <Palette className="w-5 h-5 shrink-0 mt-0.5" />
                      <p>Theme can also be toggled instantly from the top bar. Your selection here sets the default appearance across devices.</p>
                    </div>
                    <div className="mt-8 border-t border-neutral-100 dark:border-neutral-800 pt-7">
                      <AvatarPicker preference={practiceGuide} onSave={handlePracticeGuideSave} />
                    </div>
                  </>
                )}
              </Card>
            </motion.div>
          </AnimatePresence>

          {/* Danger zone */}
          <Card className="p-6 mt-6 border-coral-200 dark:border-coral-900/50">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-11 h-11 bg-coral-100 dark:bg-coral-900/30 rounded-xl flex items-center justify-center shrink-0">
                  <Trash2 className="w-5 h-5 text-coral-600 dark:text-coral-400" />
                </div>
                <div>
                  <h3 className="font-bold text-neutral-900 dark:text-white">Delete Account</h3>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Permanently remove your account and all therapy data. This cannot be undone.</p>
                </div>
              </div>
              <button
                onClick={() => setShowDelete(true)}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold bg-coral-50 dark:bg-coral-900/20 text-coral-600 dark:text-coral-400 hover:bg-coral-100 dark:hover:bg-coral-900/30 transition shrink-0"
              >
                Delete Account
              </button>
            </div>
          </Card>
        </div>
      </div>

      {/* Delete confirm modal */}
      <AnimatePresence>
        {showDelete && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/60 backdrop-blur-sm"
            onClick={() => setShowDelete(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md bg-white dark:bg-neutral-900 rounded-3xl shadow-xl p-6 border border-neutral-100 dark:border-neutral-800"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 bg-coral-100 dark:bg-coral-900/30 rounded-xl flex items-center justify-center">
                    <AlertTriangle className="w-5 h-5 text-coral-600 dark:text-coral-400" />
                  </div>
                  <h3 className="text-lg font-bold text-neutral-900 dark:text-white">Delete Account?</h3>
                </div>
                <button onClick={() => setShowDelete(false)} className="p-1.5 text-neutral-400 hover:text-neutral-700 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
                This will permanently delete your account, your child's progress, and all therapy records. Type <span className="font-bold text-coral-600">DELETE</span> to confirm.
              </p>
              <input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="DELETE"
                className="w-full px-4 py-2.5 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 outline-none focus:ring-2 focus:ring-coral-200 text-neutral-800 dark:text-white mb-4"
              />
              <div className="flex gap-3">
                <button onClick={() => setShowDelete(false)} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-semibold bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 transition">
                  Cancel
                </button>
                <button onClick={handleDelete} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-semibold bg-coral-500 text-white hover:bg-coral-600 transition">
                  Delete Forever
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </DashboardLayout>
  )
}

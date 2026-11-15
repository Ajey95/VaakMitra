import { Camera, Gauge, PartyPopper, RotateCcw, Sparkles, Volume2 } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useInteractionSettingsStore } from '../../store/interactionSettingsStore'
import './interaction.css'

const ENGLISH_SELECTS = [
  { key: 'ageBand', label: 'Presentation', icon: Sparkles, options: [['early', 'Ages 4–6'], ['middle', 'Ages 7–9'], ['older', 'Ages 10–12']] },
  { key: 'motionLevel', label: 'Movement', icon: Gauge, options: [['full', 'Full'], ['reduced', 'Reduced'], ['minimal', 'Minimal']] },
  { key: 'celebrationLevel', label: 'Celebrations', icon: PartyPopper, options: [['full', 'Full'], ['gentle', 'Gentle'], ['none', 'None']] },
  { key: 'sessionPace', label: 'Pace', icon: Gauge, options: [['guided', 'Guided'], ['self', 'Self-paced']] },
]

const ENGLISH_TOGGLES = [
  { key: 'soundEnabled', label: 'Activity sounds', icon: Volume2 },
  { key: 'spokenPrompts', label: 'Spoken instructions', icon: Volume2 },
  { key: 'cameraEnabled', label: 'Allow camera activities', icon: Camera },
]

const TAMIL_SELECTS = [
  { key: 'ageBand', label: 'வயதுக்கேற்ற தோற்றம்', icon: Sparkles, options: [['early', '4–6 வயது'], ['middle', '7–9 வயது'], ['older', '10–12 வயது']] },
  { key: 'motionLevel', label: 'அசைவு', icon: Gauge, options: [['full', 'முழு'], ['reduced', 'குறைவு'], ['minimal', 'மிகக் குறைவு']] },
  { key: 'celebrationLevel', label: 'கொண்டாட்டம்', icon: PartyPopper, options: [['full', 'முழு'], ['gentle', 'மென்மை'], ['none', 'வேண்டாம்']] },
  { key: 'sessionPace', label: 'வேகம்', icon: Gauge, options: [['guided', 'வழிகாட்டலுடன்'], ['self', 'என் வேகத்தில்']] },
]

const TAMIL_TOGGLES = [
  { key: 'soundEnabled', label: 'விளையாட்டு ஒலிகள்', icon: Volume2 },
  { key: 'spokenPrompts', label: 'குரல் வழிமுறைகள்', icon: Volume2 },
  { key: 'cameraEnabled', label: 'கேமரா விளையாட்டுகளை அனுமதி', icon: Camera },
]

const BILINGUAL_SELECTS = ENGLISH_SELECTS.map((english, index) => ({
  ...english,
  label: `${english.label} / ${TAMIL_SELECTS[index].label}`,
  options: english.options.map(([value, text], optionIndex) => [
    value,
    `${text} / ${TAMIL_SELECTS[index].options[optionIndex][1]}`,
  ]),
}))

const BILINGUAL_TOGGLES = ENGLISH_TOGGLES.map((english, index) => ({
  ...english,
  label: `${english.label} / ${TAMIL_TOGGLES[index].label}`,
}))

export default function SensorySettingsPanel({ onDone, locale = 'en' }) {
  const childAge = useAuthStore((state) => state.user?.child_age)
  const { preferences, updatePreference, resetPreferences } = useInteractionSettingsStore()
  const tamil = locale === 'ta'
  const bilingual = locale === 'bi'
  const selects = tamil ? TAMIL_SELECTS : bilingual ? BILINGUAL_SELECTS : ENGLISH_SELECTS
  const toggles = tamil ? TAMIL_TOGGLES : bilingual ? BILINGUAL_TOGGLES : ENGLISH_TOGGLES
  const heading = tamil
    ? 'விளையாட்டை வசதியாக மாற்றலாம்'
    : bilingual ? 'Make practice feel comfortable / விளையாட்டை வசதியாக மாற்றலாம்' : 'Make practice feel comfortable'
  const description = tamil
    ? 'இந்தத் தேர்வுகளை எப்போது வேண்டுமானாலும் மாற்றலாம்.'
    : bilingual ? 'A caregiver can change these choices at any time / இந்தத் தேர்வுகளை எப்போது வேண்டுமானாலும் மாற்றலாம்.' : 'A caregiver can change these choices at any time.'
  const resetLabel = tamil ? 'மீட்டமை' : bilingual ? 'Reset / மீட்டமை' : 'Reset'
  const saveLabel = tamil ? 'தேர்வுகளைச் சேமிக்கவும்' : bilingual ? 'Save choices / தேர்வுகளைச் சேமிக்கவும்' : 'Save choices'

  return (
    <section className="interactive-settings" aria-labelledby="interaction-settings-title">
      <div className="interactive-settings__heading">
        <div>
          <h2 id="interaction-settings-title">{heading}</h2>
          <p>{description}</p>
        </div>
        <button className="interactive-control interactive-settings__reset" type="button" onClick={() => resetPreferences({ age: childAge })}>
          <RotateCcw aria-hidden="true" /> {resetLabel}
        </button>
      </div>

      <div className="interactive-settings__grid">
        {selects.map(({ key, label, icon: Icon, options }) => (
          <label key={key} className="interactive-settings__field">
            <span><Icon aria-hidden="true" /> {label}</span>
            <select value={preferences[key]} onChange={(event) => updatePreference(key, event.target.value)}>
              {options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
            </select>
          </label>
        ))}
      </div>

      <div className="interactive-settings__toggles">
        {toggles.map(({ key, label, icon: Icon }) => (
          <label key={key} className="interactive-settings__toggle">
            <Icon aria-hidden="true" />
            <span>{label}</span>
            <input
              type="checkbox"
              checked={preferences[key]}
              onChange={(event) => updatePreference(key, event.target.checked)}
            />
          </label>
        ))}
      </div>

      {onDone ? <button type="button" className="interactive-control interactive-primary-button" onClick={onDone}>{saveLabel}</button> : null}
    </section>
  )
}

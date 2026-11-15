import { useEffect, useState } from 'react'
import { Check, Heart, Pause, Sparkles, Volume2 } from 'lucide-react'
import { AVATAR_CATALOG, AVATAR_MOTION_LEVELS, AVATAR_PALETTES, avatarById } from '../../features/avatar/avatarCatalog'
import { normalizeAvatarPreference } from '../../features/avatar/avatarPreference'
import ExpressiveAvatar from './ExpressiveAvatar'
import './AvatarPicker.css'

const REACTIONS = [
  { phase: 'IDLE', label: 'Hello', icon: Heart },
  { phase: 'PROMPTING', label: 'Speaking', icon: Volume2 },
  { phase: 'LISTENING', label: 'Listening', icon: Pause },
  { phase: 'PRAISE', label: 'Celebrate', icon: Sparkles },
]

export default function AvatarPicker({ preference, onSave = () => {} }) {
  const [draft, setDraft] = useState(() => normalizeAvatarPreference(preference))
  const [phase, setPhase] = useState('IDLE')
  const selected = avatarById(draft.avatarId)

  useEffect(() => setDraft(normalizeAvatarPreference(preference)), [preference])

  const update = (patch) => setDraft((current) => normalizeAvatarPreference({ ...current, ...patch }))

  return <section className="avatar-picker" aria-label="Choose a practice guide">
    <div className="avatar-picker__heading">
      <div><span>Practice companion</span><h3>Choose a guide your child feels comfortable with</h3></div>
      <p>Each guide follows the same safe practice flow. Only the look, colours, and amount of movement change.</p>
    </div>

    <div className="avatar-picker__workspace">
      <div className="avatar-picker__preview" aria-label={`Preview ${selected.name}`}>
        <span className="avatar-picker__preview-kicker">LIVE PREVIEW</span>
        <div className="avatar-picker__speech"><strong>{selected.name}</strong><span>{phase === 'PRAISE' ? 'Wonderful try! You stayed with the whole word.' : phase === 'LISTENING' ? 'I’m listening. Take your time.' : phase === 'PROMPTING' ? 'Listen first, then we’ll say it together.' : 'Hello! I’ll practise with you, one step at a time.'}</span></div>
        <ExpressiveAvatar avatarId={draft.avatarId} paletteId={draft.paletteId} motionLevel={draft.motionLevel} phase={phase} speaking={phase === 'PROMPTING'} audioLevel={.68}/>
        <div className="avatar-picker__reactions" aria-label="Preview reactions">
          <span>Preview reactions</span>
          <div>{REACTIONS.map(({ phase: value, label, icon: Icon }) => <button key={value} type="button" className={phase === value ? 'is-active' : ''} aria-pressed={phase === value} onClick={() => setPhase(value)}><Icon aria-hidden="true"/>{label}</button>)}</div>
        </div>
      </div>

      <div className="avatar-picker__controls">
        <fieldset><legend>1. Pick a guide</legend><div className="avatar-picker__identity-grid">
          {AVATAR_CATALOG.map((avatar) => <button key={avatar.id} type="button" data-selected={draft.avatarId === avatar.id} aria-pressed={draft.avatarId === avatar.id} onClick={() => update({ avatarId: avatar.id })}>
            <span className="avatar-picker__mini"><ExpressiveAvatar avatarId={avatar.id} paletteId={draft.paletteId} motionLevel="still"/></span>
            <span><strong>{avatar.name}</strong><small>{avatar.description}</small></span>
            {draft.avatarId === avatar.id ? <Check aria-hidden="true"/> : null}
          </button>)}
        </div></fieldset>

        <fieldset><legend>2. Choose colours</legend><div className="avatar-picker__swatches">
          {AVATAR_PALETTES.map((palette) => <button key={palette.id} type="button" className={`avatar-picker__swatch avatar-picker__swatch--${palette.id}`} aria-label={palette.name} aria-pressed={draft.paletteId === palette.id} onClick={() => update({ paletteId: palette.id })}><span/>{draft.paletteId === palette.id ? <Check aria-hidden="true"/> : null}</button>)}
        </div></fieldset>

        <fieldset><legend>3. Set movement</legend><div className="avatar-picker__motion-options">
          {AVATAR_MOTION_LEVELS.map((motion) => <button key={motion.id} type="button" aria-pressed={draft.motionLevel === motion.id} onClick={() => update({ motionLevel: motion.id })}><strong>{motion.name}</strong><small>{motion.description}</small></button>)}
        </div></fieldset>

        <button type="button" className="avatar-picker__save" onClick={() => onSave(normalizeAvatarPreference(draft))}><Check aria-hidden="true"/>Use this guide</button>
        <p className="avatar-picker__privacy">Saved for this child on this device. No photo or custom upload is needed.</p>
      </div>
    </div>
  </section>
}

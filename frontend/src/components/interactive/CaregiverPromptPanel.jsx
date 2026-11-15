import { ChevronDown, HandHeart } from 'lucide-react'
import { ASSISTANCE_LEVELS } from '../../features/together/talkTogetherActivity'

const LABELS = {
  independent: 'Independent',
  verbal_prompt: 'Verbal cue',
  visual_prompt: 'Visual cue',
  modelled: 'Modelled first',
  skipped: 'Skipped',
}

export default function CaregiverPromptPanel({ mission, assistance, onAssistanceChange }) {
  return (
    <details className="caregiver-panel">
      <summary><span><HandHeart aria-hidden="true" /> Grown-up guide</span><ChevronDown aria-hidden="true" /></summary>
      <div className="caregiver-panel__body">
        <p>{mission.caregiverCue}</p>
        <fieldset>
          <legend>What support was used?</legend>
          <div className="caregiver-panel__options">
            {ASSISTANCE_LEVELS.map((level) => (
              <label key={level} className={assistance === level ? 'is-selected' : ''}>
                <input type="radio" name="assistance" value={level} checked={assistance === level} onChange={() => onAssistanceChange(level)} />
                {LABELS[level]}
              </label>
            ))}
          </div>
        </fieldset>
      </div>
    </details>
  )
}

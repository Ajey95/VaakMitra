import React from 'react'
import { avatarById } from '../../features/avatar/avatarCatalog'
import { mouthForAudio, presentationForPhase } from '../../features/avatar/avatarPresentation'
import PippinRig from './PippinRig'
import WarmHumanRig from './WarmHumanRig'
import './ExpressiveAvatar.css'

/** DEC-026/AVT-003..005: local renderer; phase drives bounded expression and gesture only. */
export default function ExpressiveAvatar({
  avatarId = 'meera',
  paletteId = 'coral-teal',
  phase = 'IDLE',
  speaking = false,
  audioLevel = 0,
  motionLevel = 'gentle',
  className = '',
}) {
  const avatar = avatarById(avatarId)
  const presentation = presentationForPhase(phase, motionLevel)
  const mouth = mouthForAudio(speaking, audioLevel)

  return <div
    className={`expressive-avatar ${className}`.trim()}
    role="img"
    aria-label={`${avatar.name}, expressive avatar guide`}
    data-avatar-id={avatar.id}
    data-avatar-kind={avatar.kind}
    data-avatar-phase={phase}
    data-expression={presentation.expression}
    data-gesture={presentation.gesture}
    data-motion={presentation.motion}
    data-mouth={mouth}
  >
    {avatar.kind === 'animal'
      ? <PippinRig paletteId={paletteId} mouth={mouth}/>
      : <WarmHumanRig avatarId={avatar.id} paletteId={paletteId} mouth={mouth}/>
    }
  </div>
}

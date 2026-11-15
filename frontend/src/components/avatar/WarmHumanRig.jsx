import React from 'react'

const IDENTITIES = {
  meera: { skin: '#B96F49', skinShadow: '#955033', hair: '#2B2032', shirt: '#168D92', accent: '#F3B85A', hairStyle: 'long' },
  kavin: { skin: '#9B5C3D', skinShadow: '#78412E', hair: '#241C24', shirt: '#386FC7', accent: '#F5C15B', hairStyle: 'short' },
  nila: { skin: '#7E4C37', skinShadow: '#613726', hair: '#3A253E', shirt: '#9A5BC3', accent: '#55C8BB', hairStyle: 'curl' },
}

const PALETTES = {
  'coral-teal': { shirt: '#168D92', accent: '#F07E6E' },
  sunrise: { shirt: '#D86651', accent: '#F4BE55' },
  lotus: { shirt: '#8B5BB5', accent: '#E486A5' },
}

export default function WarmHumanRig({ avatarId, paletteId = 'coral-teal', mouth = 'neutral' }) {
  const identity = IDENTITIES[avatarId] ?? IDENTITIES.meera
  const palette = PALETTES[paletteId] ?? PALETTES['coral-teal']
  const shirt = avatarId === 'meera' ? palette.shirt : identity.shirt
  const accent = palette.accent ?? identity.accent
  const grad = `${avatarId}-shirt-${paletteId}`
  const skinGrad = `${avatarId}-skin`
  const selectedMouth = `mouth-${mouth}`

  return <svg className="expressive-rig expressive-rig--human" viewBox="0 0 320 390" aria-hidden="true">
    <defs>
      <linearGradient id={grad} x1="0" y1="0" x2="1" y2="1"><stop stopColor={shirt} /><stop offset="1" stopColor="#284D70" /></linearGradient>
      <linearGradient id={skinGrad} x1="0" y1="0" x2=".8" y2="1"><stop stopColor={identity.skin} /><stop offset="1" stopColor={identity.skinShadow} /></linearGradient>
      <filter id={`${avatarId}-soft`} x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="5" stdDeviation="5" floodOpacity=".14" /></filter>
    </defs>
    <ellipse className="expressive-rig__shadow" cx="160" cy="369" rx="92" ry="13" />

    <g className="expressive-rig__arm expressive-rig__arm--left" data-avatar-part="arm-left">
      <path d="M104 263C73 268 54 292 48 326c-2 14 6 23 18 24 12 1 19-7 21-18l24-58z" fill={`url(#${skinGrad})`} />
      <g data-avatar-part="hand-left"><path d="M49 324c-9 4-16 17-11 27 5 11 22 13 31 5 8-7 8-21-1-28-5-4-12-6-19-4z" fill={identity.skin} /><path d="M43 331l-6 11M50 329l-3 14M58 329l1 14" stroke={identity.skinShadow} strokeWidth="3" strokeLinecap="round" /></g>
    </g>
    <g className="expressive-rig__arm expressive-rig__arm--right" data-avatar-part="arm-right">
      <path d="M216 263c31 5 50 29 56 63 2 14-6 23-18 24-12 1-19-7-21-18l-24-58z" fill={`url(#${skinGrad})`} />
      <g data-avatar-part="hand-right"><path d="M271 324c9 4 16 17 11 27-5 11-22 13-31 5-8-7-8-21 1-28 5-4 12-6 19-4z" fill={identity.skin} /><path d="M277 331l6 11M270 329l3 14M262 329l-1 14" stroke={identity.skinShadow} strokeWidth="3" strokeLinecap="round" /></g>
    </g>

    <path d="M101 265c16-18 38-26 59-26s43 8 59 26l20 101H81z" fill={`url(#${grad})`} filter={`url(#${avatarId}-soft)`} data-avatar-part="torso" />
    <path d="M128 253l32 37 32-37" fill={accent} opacity=".95" />
    <path d="M142 236h36v34c-10 11-26 11-36 0z" fill={identity.skin} data-avatar-part="neck" />
    <path d="M150 285v78M170 285v78" stroke="#fff" strokeOpacity=".32" strokeWidth="3" />

    <g className="expressive-rig__head" data-avatar-part="head" filter={`url(#${avatarId}-soft)`}>
      {identity.hairStyle === 'long' && <path d="M91 117c3-59 34-89 72-89 46 0 75 34 73 101l-7 105c-20 18-40 25-67 24-27 1-54-7-72-27z" fill={identity.hair} data-avatar-part="hair-back" />}
      {identity.hairStyle === 'short' && <path d="M94 121c-7-55 20-91 67-91 46 0 77 27 72 85-18-25-43-38-74-37-28 1-49 14-65 43z" fill={identity.hair} data-avatar-part="hair-back" />}
      {identity.hairStyle === 'curl' && <g fill={identity.hair} data-avatar-part="hair-back"><circle cx="111" cy="62" r="29"/><circle cx="151" cy="48" r="34"/><circle cx="194" cy="64" r="32"/><circle cx="218" cy="102" r="30"/><circle cx="101" cy="106" r="30"/></g>}
      <path d="M141 204h38v61q-19 14-38 0z" fill={identity.skin} />
      <ellipse cx="160" cy="143" rx="68" ry="78" fill={`url(#${skinGrad})`} />
      <ellipse cx="94" cy="145" rx="12" ry="21" fill={identity.skin} /><ellipse cx="226" cy="145" rx="12" ry="21" fill={identity.skin} />
      <path d="M96 116c14-51 37-67 68-68 36 0 60 20 66 67-23-7-42-20-55-40-17 18-43 32-79 41z" fill={identity.hair} data-avatar-part="hair-front" />
      <g className="expressive-rig__brow expressive-rig__brow--left" data-avatar-part="brow-left"><path d="M116 127q17-10 31 0" fill="none" stroke="#3A292A" strokeWidth="5" strokeLinecap="round" /></g>
      <g className="expressive-rig__brow expressive-rig__brow--right" data-avatar-part="brow-right"><path d="M174 127q17-10 31 0" fill="none" stroke="#3A292A" strokeWidth="5" strokeLinecap="round" /></g>
      <g className="expressive-rig__eye expressive-rig__eye--left" data-avatar-part="eye-left"><ellipse cx="132" cy="146" rx="12" ry="15" fill="#fff"/><ellipse cx="134" cy="148" rx="7" ry="10" fill="#332C31"/><circle cx="131" cy="144" r="3" fill="#fff"/></g>
      <g className="expressive-rig__eye expressive-rig__eye--right" data-avatar-part="eye-right"><ellipse cx="190" cy="146" rx="12" ry="15" fill="#fff"/><ellipse cx="188" cy="148" rx="7" ry="10" fill="#332C31"/><circle cx="185" cy="144" r="3" fill="#fff"/></g>
      <ellipse className="expressive-rig__cheek" data-avatar-part="cheek-left" cx="119" cy="175" rx="17" ry="8" fill="#ED887F" opacity=".34" />
      <ellipse className="expressive-rig__cheek" data-avatar-part="cheek-right" cx="202" cy="175" rx="17" ry="8" fill="#ED887F" opacity=".34" />
      <path d="M160 145l-5 24 10 2" fill="none" stroke={identity.skinShadow} strokeWidth="3" strokeLinecap="round" data-avatar-part="nose" />
      <g className={`expressive-rig__mouth ${selectedMouth}`}>
        <path data-avatar-part="mouth-neutral" d="M145 192q15 10 30 0" fill="none" stroke="#71343F" strokeWidth="5" strokeLinecap="round" />
        <path data-avatar-part="mouth-m" d="M145 193q15 4 30 0" fill="none" stroke="#71343F" strokeWidth="6" strokeLinecap="round" />
        <ellipse data-avatar-part="mouth-a" cx="160" cy="194" rx="15" ry="13" fill="#71343F"/><path className="expressive-rig__teeth expressive-rig__teeth--a" d="M148 190q12-5 24 0" stroke="#fff" strokeWidth="5" />
        <ellipse data-avatar-part="mouth-e" cx="160" cy="194" rx="18" ry="8" fill="#71343F"/><path className="expressive-rig__teeth expressive-rig__teeth--e" d="M146 192h28" stroke="#fff" strokeWidth="4" />
        <ellipse data-avatar-part="mouth-o" cx="160" cy="194" rx="10" ry="13" fill="#71343F"/>
      </g>
      {avatarId === 'meera' && <circle cx="160" cy="105" r="4" fill="#9E294A" />}
      <path d="M132 218q28 13 56 0" fill="none" stroke="#fff" strokeOpacity=".16" strokeWidth="3" />
    </g>
  </svg>
}

import React from 'react'

const PALETTES = {
  'coral-teal': { fur: '#E4974E', shadow: '#BC6C35', scarf: '#168D92', accent: '#F07E6E' },
  sunrise: { fur: '#EDAA55', shadow: '#C37738', scarf: '#D86651', accent: '#F4BE55' },
  lotus: { fur: '#D39A64', shadow: '#A86D45', scarf: '#8B5BB5', accent: '#E486A5' },
}

export default function PippinRig({ paletteId = 'coral-teal', mouth = 'neutral' }) {
  const palette = PALETTES[paletteId] ?? PALETTES['coral-teal']
  const selectedMouth = `mouth-${mouth}`

  return <svg className="expressive-rig expressive-rig--pippin" viewBox="0 0 320 390" aria-hidden="true">
    <defs>
      <linearGradient id="pippin-fur" x1="0" y1="0" x2="1" y2="1"><stop stopColor={palette.fur}/><stop offset="1" stopColor={palette.shadow}/></linearGradient>
      <linearGradient id="pippin-shirt" x1="0" y1="0" x2="0" y2="1"><stop stopColor={palette.scarf}/><stop offset="1" stopColor="#295174"/></linearGradient>
      <filter id="pippin-soft" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="5" stdDeviation="5" floodOpacity=".14"/></filter>
    </defs>
    <ellipse className="expressive-rig__shadow" cx="160" cy="369" rx="88" ry="13"/>
    <g className="expressive-rig__arm expressive-rig__arm--left" data-avatar-part="arm-left">
      <path d="M105 265c-31 8-48 39-47 68 0 13 9 21 20 20 12-1 18-10 17-22l18-61z" fill={`url(#pippin-fur)`}/>
      <g data-avatar-part="hand-left"><ellipse cx="62" cy="339" rx="19" ry="20" fill={palette.fur}/><circle cx="55" cy="338" r="3" fill={palette.shadow}/><circle cx="62" cy="334" r="3" fill={palette.shadow}/><circle cx="69" cy="338" r="3" fill={palette.shadow}/></g>
    </g>
    <g className="expressive-rig__arm expressive-rig__arm--right" data-avatar-part="arm-right">
      <path d="M215 265c31 8 48 39 47 68 0 13-9 21-20 20-12-1-18-10-17-22l-18-61z" fill={`url(#pippin-fur)`}/>
      <g data-avatar-part="hand-right"><ellipse cx="258" cy="339" rx="19" ry="20" fill={palette.fur}/><circle cx="251" cy="338" r="3" fill={palette.shadow}/><circle cx="258" cy="334" r="3" fill={palette.shadow}/><circle cx="265" cy="338" r="3" fill={palette.shadow}/></g>
    </g>
    <path data-avatar-part="torso" d="M105 265c15-19 34-27 55-27s40 8 55 27l23 101H82z" fill="url(#pippin-shirt)" filter="url(#pippin-soft)"/>
    <path d="M116 264l44 31 44-31-11-17h-66z" fill={palette.accent}/>
    <g className="expressive-rig__head" data-avatar-part="head" filter="url(#pippin-soft)">
      <path d="M103 102 85 42l58 34M217 102l18-60-58 34" fill={`url(#pippin-fur)`} stroke={palette.shadow} strokeWidth="5" strokeLinejoin="round" data-avatar-part="ears"/>
      <path d="m99 85-7-29 29 24M221 85l7-29-29 24" fill="#F3B5A4"/>
      <ellipse cx="160" cy="148" rx="75" ry="78" fill="url(#pippin-fur)"/>
      <path d="M111 106q49-49 98 0c-17-8-31-11-49-11s-32 3-49 11z" fill="#FFF4DA" opacity=".5" data-avatar-part="hair-front"/>
      <g className="expressive-rig__brow expressive-rig__brow--left" data-avatar-part="brow-left"><path d="M112 129q18-10 32 0" fill="none" stroke="#57382B" strokeWidth="5" strokeLinecap="round"/></g>
      <g className="expressive-rig__brow expressive-rig__brow--right" data-avatar-part="brow-right"><path d="M176 129q18-10 32 0" fill="none" stroke="#57382B" strokeWidth="5" strokeLinecap="round"/></g>
      <g className="expressive-rig__eye expressive-rig__eye--left" data-avatar-part="eye-left"><ellipse cx="130" cy="149" rx="13" ry="16" fill="#fff"/><ellipse cx="132" cy="151" rx="7" ry="11" fill="#40302F"/><circle cx="129" cy="146" r="3" fill="#fff"/></g>
      <g className="expressive-rig__eye expressive-rig__eye--right" data-avatar-part="eye-right"><ellipse cx="190" cy="149" rx="13" ry="16" fill="#fff"/><ellipse cx="188" cy="151" rx="7" ry="11" fill="#40302F"/><circle cx="185" cy="146" r="3" fill="#fff"/></g>
      <ellipse data-avatar-part="cheek-left" cx="115" cy="178" rx="17" ry="8" fill="#F18278" opacity=".38"/><ellipse data-avatar-part="cheek-right" cx="205" cy="178" rx="17" ry="8" fill="#F18278" opacity=".38"/>
      <path data-avatar-part="nose" d="m160 163-9 8 9 7 9-7z" fill="#6E3D41"/>
      <path d="M160 178v8" stroke="#6E3D41" strokeWidth="3" strokeLinecap="round"/>
      <g className={`expressive-rig__mouth ${selectedMouth}`}>
        <path data-avatar-part="mouth-neutral" d="M141 190q9 13 19 1 10 12 19-1" fill="none" stroke="#6E3D41" strokeWidth="5" strokeLinecap="round"/>
        <path data-avatar-part="mouth-m" d="M143 194q17 4 34 0" fill="none" stroke="#6E3D41" strokeWidth="6" strokeLinecap="round"/>
        <ellipse data-avatar-part="mouth-a" cx="160" cy="196" rx="15" ry="14" fill="#6E3D41"/><path className="expressive-rig__teeth expressive-rig__teeth--a" d="M149 191q11-4 22 0" stroke="#fff" strokeWidth="4"/>
        <ellipse data-avatar-part="mouth-e" cx="160" cy="195" rx="19" ry="8" fill="#6E3D41"/><path className="expressive-rig__teeth expressive-rig__teeth--e" d="M147 193h26" stroke="#fff" strokeWidth="4"/>
        <ellipse data-avatar-part="mouth-o" cx="160" cy="196" rx="10" ry="14" fill="#6E3D41"/>
      </g>
      <path d="M134 219q26 12 52 0" fill="none" stroke="#fff" strokeOpacity=".24" strokeWidth="3"/>
    </g>
    <path d="M248 303q46-30 41-69" fill="none" stroke={palette.shadow} strokeWidth="16" strokeLinecap="round" data-avatar-part="tail"/>
  </svg>
}

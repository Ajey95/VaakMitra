/** DEC-026/AVT-001: closed local avatar catalogue; no runtime asset URLs. */
export const AVATAR_CATALOG = Object.freeze([
  Object.freeze({ id: 'meera', name: 'Meera', description: 'Warm and reassuring', kind: 'human', variant: 'woman' }),
  Object.freeze({ id: 'kavin', name: 'Kavin', description: 'Friendly and encouraging', kind: 'human', variant: 'man' }),
  Object.freeze({ id: 'nila', name: 'Nila', description: 'Calm and gentle', kind: 'human', variant: 'neutral' }),
  Object.freeze({ id: 'pippin', name: 'Pippin', description: 'Playful storybook friend', kind: 'animal', variant: 'cat' }),
])

export const AVATAR_PALETTES = Object.freeze([
  Object.freeze({ id: 'coral-teal', name: 'Coral & teal' }),
  Object.freeze({ id: 'sunrise', name: 'Sunrise' }),
  Object.freeze({ id: 'lotus', name: 'Lotus' }),
])

export const AVATAR_MOTION_LEVELS = Object.freeze([
  Object.freeze({ id: 'gentle', name: 'Gentle', description: 'Natural breathing and short gestures' }),
  Object.freeze({ id: 'reduced', name: 'Reduced', description: 'Slower, smaller reactions' }),
  Object.freeze({ id: 'still', name: 'Still', description: 'Expressions without body movement' }),
])

export function avatarById(id) {
  return AVATAR_CATALOG.find((avatar) => avatar.id === id) ?? AVATAR_CATALOG[0]
}


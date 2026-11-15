export const RESPONSE_MODES = new Set([
  'choice',
  'speech',
  'airflow',
  'mouth_shape',
  'caregiver_confirm',
  'touch',
])

export function validateActivity(activity) {
  const errors = []
  if (!activity?.id || typeof activity.id !== 'string') errors.push('Activity id is required')
  if (!Array.isArray(activity?.steps) || activity.steps.length === 0) {
    errors.push('Activity must contain at least one step')
    return { valid: false, errors }
  }

  const ids = activity.steps.map((step) => step?.id)
  const knownIds = new Set(ids)
  if (knownIds.size !== ids.length) errors.push('Step ids must be unique')

  for (const step of activity.steps) {
    const id = step?.id || '(missing)'
    if (!step?.id) errors.push('Every step requires an id')
    if (!RESPONSE_MODES.has(step?.responseMode)) {
      errors.push(`Step ${id} has unsupported response mode ${step?.responseMode}`)
    }
    if (step?.responseMode === 'choice' && (!Array.isArray(step.choices) || step.choices.length < 1)) {
      errors.push(`Step ${id} requires at least one choice`)
    }
    if (Array.isArray(step?.choices) && step.choices.length > 2) {
      errors.push(`Step ${id} may expose at most two choices`)
    }
    if (step?.next && !knownIds.has(step.next)) {
      errors.push(`Step ${id} references unknown next step ${step.next}`)
    }
  }

  return { valid: errors.length === 0, errors }
}

export function assertValidActivity(activity) {
  const result = validateActivity(activity)
  if (!result.valid) throw new Error(result.errors.join('; '))
  return activity
}


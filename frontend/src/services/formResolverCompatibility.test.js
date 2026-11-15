import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'

// Exercise the library boundary used by login/registration after security upgrades.
const schema = z.object({
  email: z.string().trim().toLowerCase().email('Enter a valid email'),
  child_age: z.coerce.number().min(4).max(12),
  password: z.string().min(10),
  confirm_password: z.string(),
}).refine(value => value.password === value.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
})

const valid = {
  email: ' Demo@Example.com ',
  child_age: '7',
  password: 'TestOnlyPassword!42',
  confirm_password: 'TestOnlyPassword!42',
}
const resolve = values => zodResolver(schema)(values, {}, {
  criteriaMode: 'firstError', shouldUseNativeValidation: false, fields: {},
})

describe('form resolver compatibility', () => {
  it('returns normalized/coerced values for a valid form', async () => {
    const result = await resolve(valid)
    expect(result.errors).toEqual({})
    expect(result.values.email).toBe('demo@example.com')
    expect(result.values.child_age).toBe(7)
  })

  it('maps invalid email issues to a field error instead of throwing', async () => {
    const result = await resolve({ ...valid, email: 'not-an-email' })
    expect(result.values).toEqual({})
    expect(result.errors.email.message).toBe('Enter a valid email')
  })

  it('preserves the cross-field confirmation error path', async () => {
    const result = await resolve({ ...valid, confirm_password: 'different-test-value' })
    expect(result.errors.confirm_password.message).toBe("Passwords don't match")
  })

  it('rejects an invalid numeric input without returning submit values', async () => {
    const result = await resolve({ ...valid, child_age: 'unknown' })
    expect(result.values).toEqual({})
    expect(result.errors.child_age).toBeDefined()
  })
})

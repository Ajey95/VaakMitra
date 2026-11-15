import { expect, test } from '@playwright/test'

test('one-click demo login submits the documented credentials', async ({ page }) => {
  let submitted = null
  let submittedUrl = null
  await page.route('**/api/**', async (route) => {
    const pathname = new URL(route.request().url()).pathname
    if (pathname === '/api/auth/me') {
      return route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"Not authenticated"}' })
    }
    if (pathname === '/api/auth/login') {
      submitted = route.request().postDataJSON()
      submittedUrl = route.request().url()
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'demo-token',
          user: {
            email: 'demo@speakeasy.app',
            full_name: 'Demo Parent',
            child_name: 'Kavi',
            child_age: 7,
            role: 'user',
            total_sessions: 12,
            total_stars: 180,
            language: 'Tamil',
            is_demo: true,
          },
        }),
      })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.goto('/login')
  await page.getByRole('button', { name: 'Enter Demo' }).click()

  await expect(page).toHaveURL(/\/dashboard$/)
  expect(submitted).toEqual({ email: 'demo@speakeasy.app', password: 'Demo@1234' })
  expect(submittedUrl).toBe('http://127.0.0.1:5173/api/auth/login')
})

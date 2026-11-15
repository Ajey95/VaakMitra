import { expect, test } from '@playwright/test'
import path from 'node:path'

const CREATED_USER = {
  id: 'new-user-id',
  email: 'parent@example.com',
  full_name: 'Test Parent',
  child_name: 'Maya',
  child_age: 7,
  language: 'Tamil',
  role: 'user',
  total_sessions: 0,
  total_stars: 0,
}

async function mockRegistrationApi(page, { registerStatus = 201, detail } = {}) {
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') {
      return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) })
    }
    if (path === '/api/auth/register') {
      if (registerStatus !== 201) {
        return route.fulfill({ status: registerStatus, contentType: 'application/json', body: JSON.stringify({ detail }) })
      }
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'User registered successfully', access_token: 'memory-only-token', user: CREATED_USER }),
      })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
}

async function completeChildStep(page, { parent = 'Test Parent', child = 'Maya', age = '7' } = {}) {
  await page.getByLabel('Parent / Guardian Name').fill(parent)
  await page.getByLabel("Child's Name").fill(child)
  await page.getByLabel("Child's Age").fill(age)
  await page.getByRole('button', { name: 'Continue' }).click()
}

async function completeAccountStep(page, { email = 'parent@example.com', password = 'SafePassword1!' } = {}) {
  await page.getByLabel('Email Address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByLabel('Confirm Password').fill(password)
  await page.getByRole('checkbox').check()
}

test.beforeEach(async ({ page }) => {
  await mockRegistrationApi(page)
})

test('successful registration completes the authenticated journey', async ({ page }) => {
  let submitted
  const consoleErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  await page.route('**/api/auth/register', async (route) => {
    submitted = route.request().postDataJSON()
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'User registered successfully', access_token: 'memory-only-token', user: CREATED_USER }),
    })
  })

  await page.goto('/register', { waitUntil: 'domcontentloaded' })
  await completeChildStep(page)
  await completeAccountStep(page)
  await page.getByRole('button', { name: 'Create Account' }).click()

  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page).toHaveTitle(/VaakMitra/i)
  await expect(page.getByText('Welcome back, Maya!')).toBeVisible()
  await expect(page.locator('vite-error-overlay')).toHaveCount(0)
  expect(submitted).toMatchObject({
    full_name: 'Test Parent', child_name: 'Maya', child_age: 7,
    email: 'parent@example.com', language: 'Tamil',
    password: 'SafePassword1!', confirm_password: 'SafePassword1!',
  })
  const persisted = await page.evaluate(() => JSON.stringify({ ...localStorage }))
  expect(persisted).not.toContain('memory-only-token')
  const relevantConsoleErrors = consoleErrors.filter((message) => !message.includes('401 (Unauthorized)'))
  expect(relevantConsoleErrors).toEqual([])
  expect(consoleErrors.length).toBeLessThanOrEqual(2)
  if (process.env.REGISTRATION_QA_DIR) {
    await page.screenshot({ path: path.join(process.env.REGISTRATION_QA_DIR, 'registration-success-desktop.png'), fullPage: false })
  }
})

test('registration rejects whitespace names and accurately describes password policy', async ({ page }) => {
  await page.goto('/register', { waitUntil: 'domcontentloaded' })
  await completeChildStep(page, { parent: '   ', child: 'Maya' })

  await expect(page.getByText('Name must be at least 2 characters')).toBeVisible()
  await expect(page.getByText('Step 1 of 2')).toBeVisible()

  await page.getByLabel('Parent / Guardian Name').fill('Test Parent')
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute('placeholder', 'Minimum 10 characters')
  await page.getByLabel('Password', { exact: true }).fill('Short1!A')
  await page.getByLabel('Confirm Password').fill('Short1!A')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Create Account' }).click()
  await expect(page.getByText('Password must be at least 10 characters')).toBeVisible()
  await expect(page.getByText('Very Strong')).not.toBeVisible()
})

test('duplicate email error is visible and keeps entered account data', async ({ page }) => {
  await page.unroute('**/api/**')
  await mockRegistrationApi(page, { registerStatus: 400, detail: 'Email already registered' })
  await page.goto('/register', { waitUntil: 'domcontentloaded' })
  await completeChildStep(page)
  await completeAccountStep(page)
  await page.getByRole('button', { name: 'Create Account' }).click()

  await expect(page.getByText('Email already registered')).toBeVisible()
  await expect(page).toHaveURL(/\/register$/)
  await expect(page.getByLabel('Email Address')).toHaveValue('parent@example.com')
})

test('registration is usable at a narrow mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/register', { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Continue' })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
  if (process.env.REGISTRATION_QA_DIR) {
    await page.waitForTimeout(700)
    await page.screenshot({ path: path.join(process.env.REGISTRATION_QA_DIR, 'registration-mobile.png'), fullPage: false })
  }
})

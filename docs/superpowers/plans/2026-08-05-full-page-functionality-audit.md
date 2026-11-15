# Full Page Functionality Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the application’s visible page actions perform real navigation or UI behavior, eliminate broken media, and keep every registered route renderable against the local API.

**Architecture:** Preserve the existing React/Vite and FastAPI structure. Add browser-level regression coverage for routes and primary actions, then replace placeholder controls with existing routes, browser capabilities, or real local media. Keep API-unavailable states honest and recoverable rather than inventing backend data.

**Tech Stack:** React 18, React Router, Vite, Vitest, Playwright, FastAPI

## Global Constraints

- Preserve all pre-existing uncommitted workspace changes.
- Do not require MongoDB for the bundled demo login or page navigation.
- Do not upload raw child audio or camera data.
- Use existing local media and existing application routes; do not add remote runtime dependencies.

---

### Task 1: Page and primary-action regression coverage

**Files:**
- Create: `frontend/tests/page-functionality.spec.js`
- Modify: `frontend/tests/balloon-letters.spec.js`
- Test: `frontend/tests/page-functionality.spec.js`

**Interfaces:**
- Consumes: existing Vite app at `http://127.0.0.1:5173`, `POST /api/auth/login`, and protected React routes.
- Produces: Playwright assertions for route rendering, valid media, navigation, video playback controls, speech output, and game selection.

- [ ] **Step 1: Write failing browser tests**

Add tests that enter the demo, visit every registered user route, assert that a meaningful heading or activity label renders, and assert that every rendered image has a non-zero natural width. Add focused tests asserting that “Forgot password?” navigates to `/forgot-password`, the featured training video exposes real controls and a loadable source, “Play Sound” invokes browser speech, and Game Hub “Play” changes the playable game state or navigates to a real activity.

- [ ] **Step 2: Verify the tests fail for the observed defects**

Run: `npx playwright test tests/page-functionality.spec.js --reporter=list`

Expected: failures for the hash-only password link, missing `/assets/letters/la.png`, toast-only video/sound/game controls, or placeholder route behavior.

- [ ] **Step 3: Correct the Breath Balloon assertion contract**

Filter the captured speech list to the high-pitch phoneme profile before comparing `ah` and `buh`, so normal Tamil activity guidance does not create a false failure.

- [ ] **Step 4: Verify the corrected test still checks phoneme uniqueness**

Run: `npx playwright test tests/balloon-letters.spec.js --reporter=list`

Expected: PASS only when each expected high-pitch phoneme is spoken once.

### Task 2: Authentication and therapy-route recovery

**Files:**
- Modify: `frontend/src/pages/LoginPage.jsx`
- Modify: `frontend/src/pages/TherapyPage.jsx`
- Modify: `frontend/src/components/therapy/Slide1_Picture.jsx`
- Modify: `frontend/src/components/therapy/Slide5_Rewards.jsx`
- Test: `frontend/tests/page-functionality.spec.js`

**Interfaces:**
- Consumes: React Router `Link`, lesson fields `symbol`, `english`, `phoneme`, and `type`.
- Produces: working `/forgot-password` navigation and therapy slides without requests for nonexistent letter/star files.

- [ ] **Step 1: Replace the dead password anchor**

Use `<Link to="/forgot-password">` so keyboard and pointer activation both enter the reset flow without reloading the SPA.

- [ ] **Step 2: Remove the deleted debug action and noisy lesson logs**

Keep the visible API error detail and dashboard recovery button, but remove calls to the nonexistent `window.debugAuth` helper and development-only console logging.

- [ ] **Step 3: Render built-in accessible lesson visuals**

Render the lesson symbol/word in the picture card and render Unicode stars directly. Do not request `/assets/letters/*.png` or `/assets/stars/*.png`, because those files are not present.

- [ ] **Step 4: Verify authentication and therapy behavior**

Run: `npx playwright test tests/page-functionality.spec.js --grep "password|therapy" --reporter=list`

Expected: PASS with no broken images.

### Task 3: Replace prominent placeholder actions with real behavior

**Files:**
- Modify: `frontend/src/pages/VideosPage.jsx`
- Modify: `frontend/src/pages/LetterLearningPage.jsx`
- Modify: `frontend/src/pages/GamesPage.jsx`
- Modify: `frontend/src/pages/SettingsPage.jsx`
- Modify: `frontend/src/pages/HelpPage.jsx`
- Test: `frontend/tests/page-functionality.spec.js`

**Interfaces:**
- Consumes: bundled `src/assets/videos/pronounciation_a.mp4`, `repeatPhrase(text, options)`, React Router `navigate(path)`, and stable DOM section IDs.
- Produces: a playable local pronunciation video, audible letter pronunciation, Game Hub navigation to implemented activities, and help/settings actions that navigate or scroll to actual content.

- [ ] **Step 1: Make the video player real**

Import the bundled MP4 through Vite, display a `<video controls>` element for the featured lesson, and make the available A-video action focus or play that element. Label unavailable library items honestly instead of claiming playback.

- [ ] **Step 2: Make letter pronunciation real**

Call the existing local speech helper with the selected Tamil character and `ta-IN`; keep failure non-blocking when speech synthesis is unavailable.

- [ ] **Step 3: Route Game Hub cards to implemented experiences**

Give each card an explicit route to an existing working activity (`/games#alphabet-match`, `/play/arcade/breath-balloon`, `/play/mouth-mirror`, `/letter-learning`, `/play/quest/river-rescue`, `/rewards`). For the embedded alphabet game, scroll and focus the playable panel; for the others, navigate.

- [ ] **Step 4: Connect help and settings actions**

Map settings help cards to `/help`, `mailto:speakeasy@amrita.edu`, and `/about`. Make Help quick actions scroll to FAQ, tutorial/articles, or contact sections and expand the selected content instead of showing a placeholder toast.

- [ ] **Step 5: Verify every repaired action**

Run: `npx playwright test tests/page-functionality.spec.js --grep "video|sound|Game Hub|help" --reporter=list`

Expected: PASS with visible state or URL changes after each action.

### Task 4: Full-stack and rendered verification

**Files:**
- Verify: `frontend/`
- Verify: `backend/`

**Interfaces:**
- Consumes: npm scripts, Playwright configuration, pytest suite, local API liveness route.
- Produces: evidence that the build, unit tests, browser journeys, and API regression suite remain healthy.

- [ ] **Step 1: Run frontend static checks**

Run: `npm run lint && npm test -- --reporter=dot && npm run build`

Expected: lint PASS, 166 or more unit tests PASS, production build PASS.

- [ ] **Step 2: Run all browser journeys**

Run: `npx playwright test --reporter=list`

Expected: all Playwright tests PASS, with denied-device errors limited to scenarios that deliberately simulate denial.

- [ ] **Step 3: Run backend tests**

Run: `python -m pytest -q`

Expected: 111 backend tests PASS; environment deprecation warnings may remain, but no assertion failures.

- [ ] **Step 4: Perform a real demo route crawl**

Start FastAPI on `127.0.0.1:8000` and Vite on `127.0.0.1:5173`, enter the demo account, visit every protected route, and verify page identity, nonblank content, no framework overlay, no broken images, desktop/mobile overflow, and at least one repaired interaction.

- [ ] **Step 5: Commit only audited repair files**

Stage the plan, new tests, and explicitly modified frontend files. Confirm unrelated staged changes such as `backend/.env` remain untouched before committing.

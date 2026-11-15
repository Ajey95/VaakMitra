# Expressive Avatar Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four original parent-selectable expressive SVG guides to the responsive React experience and use the saved guide throughout practice.

**Architecture:** A pure catalogue and preference module validate child-scoped choices. Parameterized inline SVG rigs expose the same named body parts, while a renderer maps only governed avatar state to expression and gesture. The existing session flow remains authoritative.

**Tech Stack:** React 18, Vite, Vitest, Testing Library/server rendering, CSS, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-15-expressive-avatar-library-design.md`

**Execution status (2026-09-15):** Complete. Tasks 1–6 are implemented and verified with 49 Vitest files / 247 tests, ESLint, Vite build, 60/60 installed-Chrome journeys, a 390×844 persistence/overflow journey, and live local-browser inspection. The journey was added to the existing page-functionality suite rather than a separate duplicate spec.

## Global Constraints

- Implement `PG-01`, `DEC-002`, `DEC-012`, `DEC-014`, `DEC-020`, `DEC-025`, and new `DEC-026`.
- Do not accept arbitrary SVG uploads or runtime avatar downloads.
- Store only `{schemaVersion, avatarId, paletteId, motionLevel}` under a child-scoped device key.
- The renderer cannot read scores, infer emotion, or create dialogue.
- Preserve the red Break / Stop control and `prefers-reduced-motion`.

---

### Task 1: Bind DEC-026 in the SSOT

**Files:**
- Modify: `VAAKMITRA_FINAL_SSOT.md`

**Interfaces:**
- Consumes: approved expressive-avatar design.
- Produces: normative `DEC-026` and version `3.3.5` used by every implementation test.

- [ ] **Step 1:** Increment the SSOT to `3.3.5`, add `DEC-026` for curated local rigs, child-scoped selection, sensory motion levels, no untrusted SVG, and presentation-only behavior.
- [ ] **Step 2:** Add the dated change-log row and verify `git diff --check -- VAAKMITRA_FINAL_SSOT.md` exits zero.
- [ ] **Step 3:** Commit only the SSOT change with `git commit -m "docs: bind expressive avatar selection"`.

### Task 2: Catalogue and child-scoped preference

**Files:**
- Create: `frontend/src/features/avatar/avatarCatalog.js`
- Create: `frontend/src/features/avatar/avatarPreference.js`
- Create: `frontend/src/features/avatar/avatarPreference.test.js`

**Interfaces:**
- Produces: `AVATAR_CATALOG`, `DEFAULT_AVATAR_PREFERENCE`, `normalizeAvatarPreference(value)`, `avatarPreferenceKey(childId)`, `loadAvatarPreference(storage, childId)`, and `saveAvatarPreference(storage, childId, value)`.

- [ ] **Step 1:** Write failing tests proving invalid identifiers fall back to `meera`, valid choices round-trip, separate child IDs use separate keys, and raw SVG/data URLs are rejected.
- [ ] **Step 2:** Run `npm test -- src/features/avatar/avatarPreference.test.js` and confirm missing-module failure.
- [ ] **Step 3:** Implement the whitelist and version-1 preference functions without network or DOM dependencies.
- [ ] **Step 4:** Rerun the focused test and commit with `git commit -m "feat: add child scoped avatar preferences"`.

### Task 3: Original shared SVG rig and state presentation

**Files:**
- Create: `frontend/src/features/avatar/avatarPresentation.js`
- Create: `frontend/src/features/avatar/avatarPresentation.test.js`
- Create: `frontend/src/components/avatar/WarmHumanRig.jsx`
- Create: `frontend/src/components/avatar/PippinRig.jsx`
- Create: `frontend/src/components/avatar/ExpressiveAvatar.jsx`
- Create: `frontend/src/components/avatar/ExpressiveAvatar.css`
- Create: `frontend/src/components/avatar/ExpressiveAvatar.test.jsx`

**Interfaces:**
- Consumes: `avatarId`, `paletteId`, `phase`, `speaking`, `audioLevel`, `motionLevel`.
- Produces: `presentationForPhase(phase)` and `<ExpressiveAvatar ... />` with `data-avatar-id`, `data-avatar-phase`, `data-expression`, `data-gesture`, and named rig groups.

- [ ] **Step 1:** Write failing pure tests for the literal state-to-expression/gesture table and reduced/still overrides.
- [ ] **Step 2:** Write a failing renderer test requiring all four identities and required part names (`head`, both arms/hands, both eyes/brows, and five mouths).
- [ ] **Step 3:** Run both focused tests and confirm missing-module/component failures.
- [ ] **Step 4:** Implement a polished parameterized human rig for Meera, Kavin and Nila, plus an original Pippin rig. Use gradients, highlights, cheeks, fingers and asymmetric poses; keep all assets inline and original.
- [ ] **Step 5:** Implement bounded CSS reactions for greeting, prompt, listening, processing, praise, coaching, retry, break and error; disable loops under reduced motion.
- [ ] **Step 6:** Rerun focused tests and commit with `git commit -m "feat: add expressive svg avatar rigs"`.

### Task 4: Mobile-first parent picker

**Files:**
- Create: `frontend/src/components/avatar/AvatarPicker.jsx`
- Create: `frontend/src/components/avatar/AvatarPicker.css`
- Create: `frontend/src/components/avatar/AvatarPicker.test.jsx`
- Modify: `frontend/src/pages/ProfilePage.jsx`

**Interfaces:**
- Consumes: child profile identifier, saved preference and `onSave(preference)`.
- Produces: caregiver flow with identity cards, reaction preview, palette controls, motion controls and `Use this guide`.

- [ ] **Step 1:** Write a failing interaction test proving selection, preview state and normalized save output.
- [ ] **Step 2:** Run it and confirm the picker is missing.
- [ ] **Step 3:** Implement a single-column-first picker with a large preview, horizontal identity selector, reaction controls, palette swatches and three motion choices.
- [ ] **Step 4:** Integrate it into Profile Preferences and save through the child-scoped preference module.
- [ ] **Step 5:** Rerun focused tests and commit with `git commit -m "feat: add caregiver avatar picker"`.

### Task 5: Use the selected guide in sessions

**Files:**
- Modify: `frontend/src/components/therapy/InteractiveAvatar.jsx`
- Modify: `frontend/src/components/therapy/InteractiveAvatar.css`
- Modify: `frontend/src/components/therapy/InteractiveAvatar.test.jsx`
- Modify: `frontend/src/components/therapy/SlideManager.jsx`
- Modify: `frontend/src/features/backendLab/DiagnosticPanel.jsx`

**Interfaces:**
- Consumes: child-scoped preference and existing state/audio props.
- Produces: the same selected guide across parent preview, guarded session and adult engineering lab.

- [ ] **Step 1:** Extend existing tests to fail unless the selected identity and governed state reach the real SVG renderer.
- [ ] **Step 2:** Replace the fixed raster mascot stage with `ExpressiveAvatar` while preserving speech bubble, scope label, replay and red stop controls.
- [ ] **Step 3:** Ensure the lab uses a device-only preview identity when no child ID exists and the product flow uses the authenticated child ID.
- [ ] **Step 4:** Rerun component tests and commit with `git commit -m "feat: use selected avatar in practice"`.

### Task 6: Browser, mobile and documentation verification

**Files:**
- Create: `frontend/tests/avatar-picker.spec.js`
- Modify: `frontend/tests/backend-lab.spec.js`
- Modify: `frontend/tests/word-session.spec.js`
- Modify: `docs/VERIFICATION_STATUS.md`
- Modify: `docs/BACKEND_COMPLETION_CONTEXT.md`

**Interfaces:**
- Produces: executable evidence for persistence, isolation, session reactions, stop behavior and responsive layout.

- [ ] **Step 1:** Write a failing Playwright journey selecting Meera/Kavin, reloading, checking child-key isolation, then entering practice.
- [ ] **Step 2:** Verify failure before wiring is complete, then make only the integration corrections required.
- [ ] **Step 3:** Run focused Playwright at 390x844 and desktop; capture latest screenshots.
- [ ] **Step 4:** Run full Vitest, ESLint, Vite build and full Playwright.
- [ ] **Step 5:** Compare the approved direction image and final browser screenshots with `view_image`; record the fidelity ledger and update verification docs.

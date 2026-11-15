# Expressive Parent-Selectable Avatar Library Design

**Status:** Proposed for implementation review  
**Date:** 2026-09-15  
**Selected direction:** A — original warm 2.5D human illustration  
**Affected authority:** `PG-01`, `DEC-002`, `DEC-012`, `DEC-014`, `DEC-020`, `DEC-025`; proposed new `DEC-026`

## 1. Outcome

VaakMitra will replace the single fixed mascot renderer with a locally bundled library of expressive, parent-selectable SVG characters. A caregiver selects a character for a child profile before practice. The same character then appears consistently in the parent preview, engineering lab, and guarded word-practice session.

The character behaves like an attentive virtual companion without pretending to be human or creating unrestricted conversation. The existing governed session state remains authoritative. The avatar only renders the approved prompt, expression and gesture associated with that state.

## 2. Art direction

The selected visual direction is a warm, softly modelled 2.5D illustration rather than a flat geometric mascot or realistic talking head. Each character uses:

- rounded facial and body shapes;
- large but proportionate eyes with highlights and eyelids;
- brows, cheeks, nose and mouth shapes that carry expression without exaggeration;
- soft gradient shading and subtle cloth/hair texture;
- open, readable hands rather than circular limb endpoints;
- slight asymmetry so the pose feels illustrated rather than mechanically mirrored;
- a warm neutral resting expression, never a blank stare.

The first release contains four original rigs:

1. **Meera** — warm adult woman guide; default selection.
2. **Kavin** — warm adult man guide.
3. **Nila** — gender-neutral young-adult guide.
4. **Pippin** — warm storybook animal companion for children who prefer non-human characters.

Each rig supports two skin/fur palettes and three clothing/accent palettes. Names are product labels, not claims that the avatar is a person. The app never copies or embeds the web reference artwork.

## 3. Why SVG rigs

SVG keeps the experience sharp and lightweight on ordinary mobile devices. Each character is drawn as semantic groups sharing one rig contract:

```text
avatar-root
  shadow
  torso
  arm-left -> forearm-left -> hand-left
  arm-right -> forearm-right -> hand-right
  neck
  head
    hair-back / hair-front
    ear-left / ear-right
    brow-left / brow-right
    eye-left / eye-right
    pupil-left / pupil-right
    cheek-left / cheek-right
    nose
    mouth-neutral / mouth-smile / viseme-a / viseme-e / viseme-o / viseme-m
```

CSS transforms animate the grouped parts. Every rig exposes the same part names, so session behavior does not contain character-specific logic.

The mouth animation is **audio-reactive**, not phonetic lip synchronization. During locally played speech, bounded amplitude/timing drives five mouth shapes. It must not be described as detected Tamil phonemes or precise visemes.

## 4. Governed reaction map

The renderer accepts the existing state plus `speaking`, `audioLevel`, `motionLevel` and `gesture`. It never decides the therapy result.

| Session state | Face | Body and hands | Motion rule |
|---|---|---|---|
| `IDLE` | warm neutral, natural blink | relaxed open posture | subtle breathing only |
| `PROMPTING` | eye contact, speaking mouth | one open-palm explanatory gesture | one gesture per prompt |
| `LISTENING` | attentive eyes, soft smile | slight forward lean, hands still | audio meter only; no distracting wave |
| `PROCESSING` | neutral thoughtful look | hands rest; tiny head settle | no looping entertainment |
| `PRAISE` | smile, bright eyes | short two-hand lift or gentle clap | one bounded celebration, then settle |
| `COACH` | encouraging focused face | slow point/open-palm demonstration | gesture follows approved coach step |
| `RETRY` | reassuring smile | small beckon/open-palm gesture | one invitation, never pressure |
| `BREAK` | relaxed eyelids | shoulders and hands lower | slower breathing, no speech gesture |
| `ERROR` | calm neutral concern | hands still | caregiver-help state; no alarm animation |

`wave` is a greeting gesture used once when the session opens. It is not a continuous idle loop.

## 5. Sensory and accessibility rules

- The default motion level is `gentle`.
- `reduced` disables arm loops, celebration bounce, continuous mouth interpolation and decorative particles while preserving state text.
- `still` renders a stable pose with only discrete mouth swaps while speaking.
- Browser `prefers-reduced-motion` overrides the selected motion level downward.
- No flashing, camera gaze tracking, emotion inference, compliance monitoring or attention scoring is introduced.
- Gestures are bounded and state-triggered. The avatar cannot pressure a child to continue.
- The existing red Break / Stop control stays visually and behaviorally dominant.

## 6. Parent selection flow

The caregiver sees a **Choose your guide** step in the profile/preferences flow before the first practice session and may revisit it later.

1. Show all four characters in their warm idle pose.
2. Selecting a card opens a short preview with `wave`, `speak`, `listen`, `coach` and `celebrate` buttons.
3. The caregiver chooses character, palette and motion level.
4. **Use this guide** validates the choice against the local catalogue and saves it for the selected child profile.
5. Every avatar surface resolves that preference; an unknown or removed identifier falls back to `meera` with `gentle` motion.

Arbitrary SVG upload is not supported. Untrusted SVG can contain active content, and an uploaded picture does not provide the required named body, face, hand and mouth rig. Personalization comes from curated identities, palettes and accessories.

## 7. Storage and privacy

The preference schema is versioned:

```json
{
  "schemaVersion": 1,
  "avatarId": "meera",
  "paletteId": "coral-teal",
  "motionLevel": "gentle"
}
```

The web development build stores the preference locally under a key scoped by authenticated child/profile identifier. It stores no audio, biometric template, face image or generated portrait. If no child identifier is available, the parent preview uses a clearly labelled device-only preference and does not claim server synchronization.

The mobile implementation uses the same schema in encrypted local app preferences. Optional caregiver-account synchronization is outside this change and requires a separate SSOT decision.

## 8. Components and boundaries

- `avatarCatalog.js`: whitelisted identities, palettes, labels and fallback behavior.
- `avatarPreference.js`: schema validation, child-scoped storage key and migration.
- `ExpressiveAvatar.jsx`: state-to-rig renderer; no scoring or policy logic.
- `rigs/*.jsx`: one original inline SVG component per character using the shared part contract.
- `AvatarPicker.jsx`: caregiver selection and preview UI.
- `InteractiveAvatar.jsx`: speech bubble, status, controls and compatibility wrapper around `ExpressiveAvatar`.
- `ProfilePage.jsx`: caregiver entry point for avatar and motion preferences.

The existing `liveAvatarFlow` remains the only development-lab turn-state owner. The product session continues to consume backend `avatar_state` and approved prompt identifiers. No avatar component reads classifier scores or creates dialogue.

## 9. Failure handling

- Invalid stored JSON, schema version, avatar identifier or palette uses the deterministic default.
- Rendering failure shows the approved prompt and controls without the illustration; practice controls remain usable.
- Missing local speech preserves the existing visible timed-prompt fallback.
- Stop, target change, session close and unmount cancel speech and motion immediately.
- No failure selects a random character or downloads an asset during a session.

## 10. Testing and acceptance

Unit tests must prove:

- preference validation, fallback, profile-key isolation and migration;
- every catalogue rig exposes the required named parts;
- every governed state maps to one bounded expression and gesture;
- reduced/still motion overrides;
- `InteractiveAvatar` retains its accessibility and legacy message contract.

Browser tests must prove:

- a caregiver selects a character and sees it persist after reload;
- two child identifiers cannot inherit each other's preference;
- the selected character appears in the lab and guarded session;
- speaking, listening, coaching, praise, break and stop change the correct rig state;
- stop cancels active gesture/speech state;
- the picker and avatar fit 390 px mobile width with no overflow;
- arbitrary SVG files and catalogue identifiers are never accepted.

Visual acceptance compares the approved warm direction against desktop and mobile screenshots. Review points are face warmth, eye/brow expression, hands, pose asymmetry, garment/hair detail, state readability, motion restraint and responsive framing.

## 11. Reference research and provenance

- Open Peeps demonstrates modular vector arms, poses and facial emotions and is published under CC0: https://www.openpeeps.com/
- Humaaans demonstrates mix-and-match human body construction and independently positionable vector elements and is published under CC0: https://www.humaaans.com/
- DiceBear documents small CSS-animated SVG avatars, deterministic generation and `prefers-reduced-motion`: https://www.dicebear.com/animated-avatars/
- The selected warm 2.5D mood reference is not licensed into the product and will not be traced or copied: https://dribbble.com/shots/15656744-Nick-Noggin-Big-Heart

The shipped artwork is original repository-owned SVG. A provenance record will list its authoring method, creation date and absence of embedded scripts, external images, fonts or runtime network dependencies.

## 12. SSOT change control

Before implementation, increment the SSOT to `3.3.5`, add `DEC-026`, add a dated decision-log entry, and cite `DEC-026` in implementation tests. `DEC-026` will bind the curated local library, shared rig contract, child-scoped preference, sensory controls, no arbitrary upload and no policy/scoring logic in the renderer.

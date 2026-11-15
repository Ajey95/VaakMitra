# Play & Practice animation fidelity ledger

Reviewed on 2026-08-05 against the approved text design in `docs/superpowers/specs/2026-08-05-play-practice-animation-upgrade-design.md`, the generated production art, and real Chromium renders at 1440 x 1000 and 390 x 844.

## Review method

- Browser/IAB tooling was not available in this environment, so Playwright/Chromium was used as the documented fallback.
- The generated art sources and the latest implementation screenshots were inspected directly with the image viewer.
- Static screenshots verify hierarchy, composition, cropping, copy, control reachability, and responsive layout. State-mapping tests and reduced-motion browser checks verify behavior that a still image cannot show.

## Comparison ledger

| Check | Approved direction | Rendered result | Outcome |
| --- | --- | --- | --- |
| Overall hierarchy | One dominant therapy scene, progress above, actions below | All four games preserve a single clear focal scene and keep code-native actions separate from decorative art | Match |
| Breath Balloon art | Bright meadow, expressive balloon, calm target-zone feedback | Meadow source art crops cleanly at both widths; the CSS balloon remains central and readable over it | Match |
| River Rescue art | Friendly elephant, river, bridge, ambient life | Existing cohesive Kavi scene is retained and enhanced with river glints, lotus, stones, dragonfly, retry, and rainbow layers | Match with deliberate reuse |
| Mouth Mirror art | Gold magical mirror, friendly therapist, unobscured target mouth | Therapist portrait, target mouth, mirror frame, and no-camera panel remain distinct; the mouth target is never covered | Match |
| Talk Together art | Five mission-specific settings and warm co-play characters | Kitchen crop and character pairing match mission one; the same production strip provides grocery, classroom, park, and birthday states | Match |
| Tamil support | Visible and spoken Tamil should convey the same state | Tamil status regions are present alongside state-specific speech hooks; River Rescue remains Tamil-first | Match |
| Interaction feedback | Distinct idle, active, retry, success, and completion reactions | Semantic `data-*` states drive bounded CSS reactions, celebration profiles, and synchronized optional sounds | Match |
| Sensory safety | Full, gentle, none, reduced, and minimal motion modes | Shared effect profiles bound particle count and travel; Calm and system reduced-motion checks pass | Match |
| Responsive behavior | Full desktop scenes; simplified but readable mobile scenes | 390 x 844 captures stack without horizontal overflow, clipped controls, or unreadable primary copy | Match |
| Accessibility | Controls remain native, reachable, and at least 44 px | Keyboard, large-target, fallback, pause, and no-overflow browser tests pass | Match |
| Privacy and fallbacks | No stored child media; microphone/camera denial must not block play | Screen-control Breath mode and model-only Mouth mode remain usable; browser cleanup/storage checks pass | Match |
| Pippin boundary | No implementation changes to Play with Pippin | The route remains in the browser regression test but no Pippin implementation file was edited for this upgrade | Match |

## Above-the-fold copy comparison

The approved design did not require replacing the established English activity headings. The rendered headings remain `Breath Balloon`, `Mouth Mirror`, and `Talk Together`; River Rescue remains Tamil-first as `கவியின் பாலப் பயணம்`. Short English subtitles and the existing progress labels remain above the fold, while the new Tamil state guidance appears immediately beneath or inside the active scene. This is a deliberate bilingual implementation of the approved Tamil-primary direction rather than a verbatim all-Tamil rewrite.

## Accepted deviations

- The approved concept was a written interaction design rather than a full-screen raster mockup. Generated production art therefore served as the visual art-direction reference, while the existing accessible shell remained the layout reference.
- River Rescue keeps the current five-page Kavi storybook structure instead of replacing it with a separate quest renderer; animation layers were added around the existing reducer, narration, and evaluation flow.
- Desktop keeps richer scene detail. Mobile uses tighter crops and fewer decorative effects, as required by the responsive and sensory-safety sections.
- Audio and speech are opt-in browser capabilities. Failure to start optional sound does not block or alter the visual activity.

## Reviewed screenshots

- Breath Balloon: `docs/qa/breath-balloon-desktop.png`, `docs/qa/breath-balloon-mobile.png`
- River Rescue: `docs/qa/river-rescue-desktop.png`, `docs/qa/river-rescue-mobile.png`
- Mouth Mirror: `docs/qa/mouth-mirror-desktop.png`, `docs/qa/mouth-mirror-mobile.png`
- Talk Together: `docs/qa/talk-together-desktop.png`, `docs/qa/talk-together-mobile.png`

## Outcome

The implementation is visually faithful to the approved design at both target viewports. No blocking overlap, horizontal overflow, obscured therapy target, clipped primary control, or art-cropping defect was observed in the eight reviewed captures.

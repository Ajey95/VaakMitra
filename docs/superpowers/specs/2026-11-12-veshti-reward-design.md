# Veshti reward sticker design

User approved the proposed veshti/cooling-glasses reward companion with automatic personalised Tamil audio, preserving avatars/session UX. SSOT3.3.51 DEC-065 PRS-008 governs.

Use a bundled transparent original generated PNG (maroon shirt, white/gold veshti, sunglasses, vibhuti, friendly thumbs-up). Replace only the kolam artwork in existing EncouragementPanel with a fitted sticker. Keep the panel's existing heading, caption, controls and completion ownership. The sticker enters gently and settles; it stays as the completed-practice illustration, avoiding an extra disappearing overlay or session step. Small preview variants retain compact dimensions. The same existing local voice speaks the current sanitised child name; no new audio request, replay rule, network call or score. All four avatars and their picker/rendering code remain unchanged.

Approaches: full-screen reward overlay would interrupt UX; replacing a selected guide would violate the user's request. Chosen approach is the previously proposed separate reward cameo within the existing feedback card. Implementation choice: persist the settled image for readability rather than auto-dismiss the card. Still/Reduced/motion-off and system-off remain respected. No celebratory flashes or new sounds.

Verification: native public completion without replay tap must show sticker and automatic-cheer status; existing Stop/Hear again, opt-out, restored/empty completion tests remain green. Inspect normal and2x actual app-window captures. Rebuild both ABIs/JVM/lint/test; verify protected avatar/model hashes and installed APK readback. Audio probe uses public sample name only; no private child data or microphone. No claim of audible name quality or clinical benefit.

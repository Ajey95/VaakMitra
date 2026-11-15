# Guide liveliness design
User chose breathing, natural blinking and a short greeting wave, preserving all existing characters/session UX. SSOT3.3.50 DEC-026 AVT-004..006 governs. Earlier mode repair is already175JVM/3physical-native GREEN on916ab557 main.

## Approaches
Chosen: animate the existing native vector rig using the current Compose frame clock. It preserves identity, palette, offline operation and current phase flow. Breathing alone is simpler but omits the user-selected expressions. Downloaded/Lottie/video characters require new assets and change identity/dependencies, so are outside the requested scope. Exact timing/curve values below are implementation choices by the author.

## Behavior
Gentle retains8rig-unit breathing over2400ms per half cycle, adds a short blink during a5600ms idle cycle and a single1800ms greeting using the existing open-palm arm pose. Reduced retains1.5rig-unit breathing over4200ms,35% gesture distance,8400ms blink cycle and2600ms greeting. Blink normalized progress opens at0, closes smoothly at.23, opens by.26; it stays open outside.20...26. Greeting interpolates smooth poses[0,1,.6,1,.6,0] over progress0..1 and settles to rest. Eye positions/colours/identity remain; pupil height follows eyelid openness so closed lids do not leave protruding circles.

Idle features exist only while foreground, system animation enabled and policy allows idle. Still/listening/processing/break/error have no breath, blink or greeting. Existing nonidle phase gestures remain bounded. Once a greeting starts it is marked consumed; phase change/background cancels it and resume cannot replay it. Explicit Hello in the caregiver preview increments an ephemeral replay key. No new speech, child score, star, route, personal data, external API/dependency or clinical claim.

## Verification
New pure curve/policy contracts RED then GREEN; actual old916ab557 phone pixels must lack blink/greeting before renderer changes. Native pixel tests track eye-white area relative to hair position (remove breathing translation) and skin pixels in the right-hand greeting region, then return to rest. Keep the earlier Still pixel equality and radio mutual-exclusivity checks. Run JVM/lint/bothABI builds and complete retained/gallery physical suite; bind installed hashes. Inspect only public app-window PNGs. Preserve old reference roots and14protected files/12assets, with expected renderer source change. Current compressed byte-exact rollback depends on the frozen prior archive; verify reconstruction before delivery. Child comfort and benefit remain unvalidated.

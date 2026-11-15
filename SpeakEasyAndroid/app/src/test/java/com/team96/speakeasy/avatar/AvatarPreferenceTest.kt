package com.team96.speakeasy.avatar

import org.junit.Assert.assertEquals
import org.junit.Test

class AvatarPreferenceTest {
    @Test fun `AVT-001 closed catalogue normalizes unknown values`() {
        assertEquals(AvatarId.MEERA, AvatarPreference.normalize("remote-url", "neon", "wild").avatarId)
        assertEquals(AvatarPalette.CORAL_TEAL, AvatarPreference.normalize("remote-url", "neon", "wild").palette)
        assertEquals(AvatarMotion.GENTLE, AvatarPreference.normalize("remote-url", "neon", "wild").motion)
    }

    @Test fun `AVT-002 accepts each governed preference value`() {
        val preference = AvatarPreference.normalize("pippin", "lotus", "still")
        assertEquals(AvatarId.PIPPIN, preference.avatarId)
        assertEquals(AvatarPalette.LOTUS, preference.palette)
        assertEquals(AvatarMotion.STILL, preference.motion)
    }
}

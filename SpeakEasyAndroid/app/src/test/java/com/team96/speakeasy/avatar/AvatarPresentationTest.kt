package com.team96.speakeasy.avatar

import org.junit.Assert.assertEquals
import org.junit.Test

class AvatarPresentationTest {
    @Test fun `AVT-004 phases map to bounded expressions and gestures`() {
        assertEquals(AvatarExpression.ATTENTIVE, AvatarPresentation.forPhase(AvatarPhase.LISTENING).expression)
        assertEquals(AvatarGesture.CELEBRATE, AvatarPresentation.forPhase(AvatarPhase.PRAISE).gesture)
        assertEquals(AvatarGesture.INVITE, AvatarPresentation.forPhase(AvatarPhase.RETRY).gesture)
        assertEquals(AvatarGesture.STILL, AvatarPresentation.forPhase(AvatarPhase.ERROR).gesture)
    }

    @Test fun `AVT-005 still motion suppresses every gesture`() {
        assertEquals(AvatarGesture.STILL, AvatarPresentation.forPhase(AvatarPhase.PRAISE, AvatarMotion.STILL).gesture)
    }

    @Test fun `AVT-005 mouth remains approximate and bounded`() {
        assertEquals(AvatarMouth.NEUTRAL, AvatarPresentation.mouth(false, 1f))
        assertEquals(AvatarMouth.M, AvatarPresentation.mouth(true, -2f))
        assertEquals(AvatarMouth.A, AvatarPresentation.mouth(true, 4f))
    }
}

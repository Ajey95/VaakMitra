package com.team96.speakeasy.journey

import com.team96.speakeasy.ui.navigation.learnerEntryRoute
import com.team96.speakeasy.viewmodel.friendlySignInError
import org.junit.Assert.*
import org.junit.Test

/** DEC079/UX014: normal local entry, completed setup and non-technical failures. */
class LearnerEntryTest {
    @Test fun aNewProfileStartsWithIntroduction() {
        assertEquals("onboarding",learnerEntryRoute(false,false))
        assertEquals("onboarding",learnerEntryRoute(false,true))
    }
    @Test fun everyFirstProfileCompletesTheCaregiverPlan() {
        assertEquals("care_setup",learnerEntryRoute(true,false))
    }
    @Test fun aReturningConfiguredProfileGoesHome() {
        assertEquals("home",learnerEntryRoute(true,true))
    }
    @Test fun connectionFailuresOfferLocalLearningWithoutServerInstructions() {
        for(raw in listOf("Failed to connect 10.0.2.2:8000","Unable to resolve host","timeout")) {
            val message=friendlySignInError(raw)
            assertTrue(message.contains("this device"))
            assertFalse(Regex("backend|port|8000|10\\.0|development",RegexOption.IGNORE_CASE).containsMatchIn(message))
        }
        assertEquals("Invalid email or password.",friendlySignInError("HTTP 401"))
    }
}

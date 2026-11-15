package com.team96.speakeasy.ui.navigation

/** DEC079/UX014: every new profile receives a plan before entering practice. */
fun learnerEntryRoute(isLoggedIn:Boolean,carePlanConfigured:Boolean):String = when {
    !isLoggedIn -> Routes.ONBOARDING
    !carePlanConfigured -> Routes.CARE_SETUP
    else -> Routes.HOME
}

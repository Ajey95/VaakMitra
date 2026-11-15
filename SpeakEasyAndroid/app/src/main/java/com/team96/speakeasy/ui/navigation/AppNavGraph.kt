package com.team96.speakeasy.ui.navigation

import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.runtime.Composable
import androidx.compose.runtime.key
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.team96.speakeasy.ui.screens.CandleGameScreen
import com.team96.speakeasy.ui.screens.AvatarPickerScreen
import com.team96.speakeasy.ui.screens.CaregiverSetupScreen
import com.team96.speakeasy.ui.screens.CheckupScreen
import com.team96.speakeasy.ui.screens.HomeScreen
import com.team96.speakeasy.ui.screens.LetterLearningScreen
import com.team96.speakeasy.ui.screens.LessonsScreen
import com.team96.speakeasy.ui.screens.LoginScreen
import com.team96.speakeasy.ui.screens.OnboardingScreen
import com.team96.speakeasy.ui.screens.PracticeScreen
import com.team96.speakeasy.ui.screens.ProfileScreen
import com.team96.speakeasy.ui.screens.ProgressScreen
import com.team96.speakeasy.ui.screens.RegisterScreen
import com.team96.speakeasy.ui.screens.RewardsScreen
import com.team96.speakeasy.ui.screens.SessionSummaryScreen
import com.team96.speakeasy.ui.screens.SplashScreen
import com.team96.speakeasy.viewmodel.AppViewModel
import com.team96.speakeasy.viewmodel.AuthViewModel

object Routes {
    const val SPLASH = "splash"
    const val ONBOARDING = "onboarding"
    const val LOGIN = "login"
    const val REGISTER = "register"
    const val HOME = "home"
    const val LESSONS = "lessons"
    const val LETTER = "letter"
    const val PRACTICE = "practice"
    const val CANDLE = "candle"
    const val PROGRESS = "progress"
    const val REWARDS = "rewards"
    const val PROFILE = "profile"
    const val AVATAR_PICKER = "avatar_picker"
    const val CARE_SETUP = "care_setup"
    const val SUMMARY = "summary"
    const val CHECKUP = "checkup"
}

@Composable
fun AppNavGraph() {
    val nav = rememberNavController()
    val authVm: AuthViewModel = viewModel()
    val appVm: AppViewModel = viewModel()

    NavHost(
        navController = nav,
        startDestination = Routes.SPLASH,
        enterTransition = { slideIntoContainer(AnimatedContentTransitionScope.SlideDirection.Left, tween(380)) + fadeIn(tween(380)) },
        exitTransition = { fadeOut(tween(250)) },
        popEnterTransition = { fadeIn(tween(300)) },
        popExitTransition = { slideOutOfContainer(AnimatedContentTransitionScope.SlideDirection.Right, tween(380)) + fadeOut(tween(380)) },
    ) {
        composable(Routes.SPLASH) { SplashScreen(nav) }
        composable(Routes.ONBOARDING) { OnboardingScreen(nav) }
        composable(Routes.LOGIN) { LoginScreen(nav, authVm) }
        composable(Routes.REGISTER) { RegisterScreen(nav, authVm) }
        composable(Routes.HOME) { HomeScreen(nav, appVm) }
        composable("${Routes.LESSONS}?section={section}",arguments=listOf(navArgument("section"){type=NavType.StringType;defaultValue=""})) { entry ->
            LessonsScreen(nav,appVm,entry.arguments?.getString("section").orEmpty())
        }
        composable(
            "${Routes.PRACTICE}/{lessonId}?focused={focused}",
            arguments = listOf(navArgument("lessonId") { type = NavType.IntType }, navArgument("focused") { type = NavType.BoolType; defaultValue = false })
        ) { entry ->
            val id = entry.arguments?.getInt("lessonId") ?: 1
            PracticeScreen(nav, appVm, id, focusedWords = entry.arguments?.getBoolean("focused") ?: false)
        }
        composable(
            "${Routes.LETTER}/{letterId}",
            arguments = listOf(navArgument("letterId") { type = NavType.StringType })
        ) { entry ->
            val context=LocalContext.current
            val journey by appVm.letterJourney.collectAsStateWithLifecycle()
            val ready by appVm.letterReady.collectAsStateWithLifecycle()
            val scope by appVm.letterScope.collectAsStateWithLifecycle()
            LaunchedEffect(Unit){appVm.loadLetterJourney(context)}
            key(scope){LetterLearningScreen(entry.arguments?.getString("letterId").orEmpty(),onBack={nav.popBackStack()},journey=if(appVm.letterIdentityIsCurrent())journey else com.team96.speakeasy.journey.LetterJourneySnapshot(),ready=ready && appVm.letterIdentityIsCurrent(),onPracticeComplete=appVm::completeLetter,nav=nav,vm=appVm,scopeKey=scope.orEmpty())}
        }
        composable(Routes.CANDLE) { CandleGameScreen(nav) }
        composable(Routes.PROGRESS) { ProgressScreen(nav) }
        composable(Routes.REWARDS) { RewardsScreen(nav, appVm) }
        composable(Routes.PROFILE) { ProfileScreen(nav, authVm) }
        composable(Routes.AVATAR_PICKER) { AvatarPickerScreen(nav) }
        composable(Routes.CARE_SETUP) { CaregiverSetupScreen(nav) }
        composable(Routes.SUMMARY) { val current=appVm.currentSessionSummary;SessionSummaryScreen(nav,current?.report?:com.team96.speakeasy.data.SessionManager.lastReport,current?.status,appVm) }
        composable(Routes.CHECKUP) { CheckupScreen(nav) }
    }
}

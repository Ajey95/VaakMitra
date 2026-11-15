package com.team96.speakeasy.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import com.team96.speakeasy.ui.components.*
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.foundation.border
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController
import com.team96.speakeasy.ui.components.AnimatedGradientBackground
import com.team96.speakeasy.ui.components.BouncyButton
import com.team96.speakeasy.ui.components.CuteTextField
import com.team96.speakeasy.ui.components.GlassCard
import com.team96.speakeasy.ui.components.GhostButton
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.ui.theme.GradientPlay
import com.team96.speakeasy.ui.theme.Teal
import com.team96.speakeasy.viewmodel.AuthViewModel

@Composable
fun RegisterScreen(nav: NavController, vm: AuthViewModel) {
    val state by vm.state.collectAsStateWithLifecycle()
    var fullName by rememberSaveable { mutableStateOf("") }
    var childName by rememberSaveable { mutableStateOf("") }
    var age by rememberSaveable { mutableStateOf("7") }
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var confirm by rememberSaveable { mutableStateOf("") }

    LaunchedEffect(state.loggedIn) {
        if (state.loggedIn) {
            nav.navigate(com.team96.speakeasy.ui.navigation.learnerEntryRoute(true,com.team96.speakeasy.data.SessionManager.carePlanConfigured)) { popUpTo(Routes.REGISTER) { inclusive = true } }
        }
    }

    HeritagePage {
        Column(
            Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(Modifier.height(16.dp))
            BrandLockup(compact=true)
            Spacer(Modifier.height(20.dp))
            Text("Create your account", color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 30.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
            Text("Set up your little learner's profile", color = HeritageMuted, fontSize = 15.sp)
            Spacer(Modifier.height(24.dp))

            GlassCard {
                CuteTextField(fullName, { fullName = it; vm.clearError() }, "Parent's Name")
                Spacer(Modifier.height(14.dp))
                CuteTextField(childName, { childName = it; vm.clearError() }, "Child's Name")
                Spacer(Modifier.height(14.dp))
                CuteTextField(age, { age = it.filter { c -> c.isDigit() }.take(2) }, "Age", keyboard = KeyboardType.Number)
                Spacer(Modifier.height(14.dp))
                CuteTextField(email, { email = it; vm.clearError() }, "Email", keyboard = KeyboardType.Email)
                Spacer(Modifier.height(14.dp))
                CuteTextField(password, { password = it; vm.clearError() }, "Password (min 8)", visual = PasswordVisualTransformation())
                Spacer(Modifier.height(14.dp))
                CuteTextField(confirm, { confirm = it; vm.clearError() }, "Confirm Password", visual = PasswordVisualTransformation())

                state.error?.let {
                    Spacer(Modifier.height(14.dp))
                    Text(it, color = HeritageMaroon, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                }

                Spacer(Modifier.height(22.dp))
                if (state.loading) {
                    CircularProgressIndicator(color = HeritageInk)
                } else {
                    BouncyButton("Create account", listOf(Color(0xFF6F2338), Color(0xFF4B1727))) {
                        vm.register(email, password, confirm, fullName, childName, age.toIntOrNull() ?: 0, "Tamil")
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
            Text(
                "Already have an account? Log in",
                color = HeritageInk,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(8.dp)
            )
            GhostButton("Log In") {
                nav.navigate(Routes.LOGIN)
            }
            GhostButton("Learn on this device instead") { vm.startOfflineReview() }
            Spacer(Modifier.height(24.dp))
        }
    }
}

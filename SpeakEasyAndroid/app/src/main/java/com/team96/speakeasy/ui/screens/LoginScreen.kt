package com.team96.speakeasy.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
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
import com.team96.speakeasy.ui.theme.GradientCalm
import com.team96.speakeasy.ui.theme.Sunny
import com.team96.speakeasy.viewmodel.AuthViewModel

@Composable
fun LoginScreen(nav: NavController, vm: AuthViewModel) {
    val state by vm.state.collectAsStateWithLifecycle()
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var showAccount by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(state.loggedIn) {
        if (state.loggedIn) {
            val destination = com.team96.speakeasy.ui.navigation.learnerEntryRoute(true,com.team96.speakeasy.data.SessionManager.carePlanConfigured)
            nav.navigate(destination) { popUpTo(Routes.LOGIN) { inclusive = true } }
        }
    }

    HeritagePage {
        Column(
            Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Spacer(Modifier.height(16.dp))
            BrandLockup(compact=true)
            Spacer(Modifier.height(20.dp))
            Text("Welcome to VaakMitra", color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 32.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
            Text("Let's keep learning together", color = HeritageMuted, fontSize = 16.sp)
            Spacer(Modifier.height(32.dp))

            state.error?.let { Text(it,color=HeritageMaroon,fontSize=14.sp,textAlign=TextAlign.Center);Spacer(Modifier.height(12.dp)) }
            if(state.loading) CircularProgressIndicator(color=HeritageMaroon) else {
                BouncyButton("Start learning",listOf(Color(0xFF6F2338),Color(0xFF4B1727))) { vm.startOfflineReview() }
            }
            Spacer(Modifier.height(10.dp))
            Text("Practise on this device. No account is needed.",color=HeritageMuted,fontSize=14.sp,textAlign=TextAlign.Center)
            Spacer(Modifier.height(24.dp))
            GhostButton(if(showAccount)"Hide account sign-in" else "Caregiver sign-in") { showAccount=!showAccount;vm.clearError() }
            if(showAccount) {
            Spacer(Modifier.height(16.dp))
            GlassCard {
                CuteTextField(value = email, onChange = { email = it; vm.clearError() }, label = "Email", keyboard = KeyboardType.Email)
                Spacer(Modifier.height(16.dp))
                CuteTextField(value = password, onChange = { password = it; vm.clearError() }, label = "Password", visual = PasswordVisualTransformation())

                Spacer(Modifier.height(22.dp))
                if (state.loading) {
                    CircularProgressIndicator(color = HeritageInk)
                } else {
                    BouncyButton("Log In", listOf(Color(0xFF9A7A63), Color(0xFF705747))) {
                        vm.login(email, password)
                    }
                }
            }

            Spacer(Modifier.height(20.dp))
            Text(
                "New here? Create an account",
                color = HeritageInk,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(8.dp),
            )
            GhostButton("Sign Up") {
                nav.navigate(Routes.REGISTER)
            }
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

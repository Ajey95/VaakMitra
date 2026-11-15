package com.team96.speakeasy.ui.screens

import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ChildCare
import androidx.compose.material.icons.rounded.Email
import androidx.compose.material.icons.rounded.Language
import androidx.compose.material.icons.rounded.Palette
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import com.team96.speakeasy.ui.components.*
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.ui.components.AnimatedGradientBackground
import com.team96.speakeasy.ui.components.BouncyButton
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.ui.theme.Coral
import com.team96.speakeasy.ui.theme.GradientPlay
import com.team96.speakeasy.viewmodel.AuthViewModel

data class ProfileDisplay(val parent:String,val child:String,val email:String)
@Composable
fun ProfileScreen(nav: NavController, vm: AuthViewModel,display:ProfileDisplay?=null) {
    val name = display?.parent ?: SessionManager.fullName ?: "Parent"
    val child = display?.child ?: SessionManager.childName ?: "Little Star"
    val email = display?.email ?: SessionManager.email ?: "—"

    HeritagePage {
        Column(Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Spacer(Modifier.height(34.dp))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                BackCircle { nav.popBackStack() }
                Spacer(Modifier.width(14.dp))
                Text("Profile", color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 28.sp, fontWeight = FontWeight.Bold)
            }

            Spacer(Modifier.height(28.dp))
            Box(
                Modifier.size(110.dp).clip(CircleShape).background(HeritageCard),
                contentAlignment = Alignment.Center
            ) { Text("🧒", fontSize = 56.sp) }
            Spacer(Modifier.height(14.dp))
            Text(child, color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 26.sp, fontWeight = FontWeight.Bold)
            Text("Little learner", color = HeritageMuted, fontSize = 14.sp)

            Spacer(Modifier.height(28.dp))
            Column(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(24.dp)).padding(8.dp),
                verticalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                InfoRow(Icons.Rounded.Person, "Parent", name)
                InfoRow(Icons.Rounded.Email, if(SessionManager.isOfflineReview) "Profile storage" else "Email", if(SessionManager.isOfflineReview) "On this device" else email)
                InfoRow(Icons.Rounded.ChildCare, "Child", child)
                InfoRow(Icons.Rounded.Language, "Language", "Tamil")
            }

            Spacer(Modifier.height(18.dp))
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(20.dp)).padding(16.dp)
                    .clickable { nav.navigate(Routes.AVATAR_PICKER) },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(Modifier.size(44.dp).clip(CircleShape).background(Color(0xFFF1E3D5)), contentAlignment = Alignment.Center) {
                    Icon(Icons.Rounded.Palette, null, tint = Color(0xFF6F2338))
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text("Practice companion", color = Color(0xFF382726), fontWeight = FontWeight.Bold)
                    Text("Choose character, colour & movement", color = Color(0xFF6E5952), fontSize = 12.sp)
                }
                Text("›", color = Color(0xFF6F2338), fontFamily = FontFamily.Serif, fontSize = 30.sp, fontWeight = FontWeight.Bold)
            }

            Spacer(Modifier.height(12.dp))
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(20.dp)).padding(16.dp)
                    .clickable { nav.navigate(Routes.CARE_SETUP) },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(Modifier.size(44.dp).clip(CircleShape).background(Color(0xFFF7ECE1)), contentAlignment = Alignment.Center) {
                    Icon(Icons.Rounded.Tune, null, tint = Coral)
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text("Caregiver plan", color = Color(0xFF382726), fontWeight = FontWeight.Bold)
                    Text("Age, session rhythm & interests", color = Color(0xFF6E5952), fontSize = 12.sp)
                }
                Text("›", color = Coral, fontFamily = FontFamily.Serif, fontSize = 30.sp, fontWeight = FontWeight.Bold)
            }

            Spacer(Modifier.height(28.dp))
            BouncyButton("Log Out", listOf(Coral, Color(0xFFFF5252))) {
                vm.logout {
                    nav.navigate(Routes.LOGIN) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
            Text("VaakMitra • v1.0", color = HeritageMuted, fontSize = 12.sp)
            Spacer(Modifier.height(12.dp))
        }
    }
}

@Composable
private fun InfoRow(icon: ImageVector, label: String, value: String) {
    Row(
        Modifier.fillMaxWidth().padding(14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier.size(40.dp).clip(CircleShape).background(HeritageCard),
            contentAlignment = Alignment.Center
        ) { Icon(icon, null, tint = HeritageMaroon, modifier = Modifier.size(22.dp)) }
        Spacer(Modifier.width(14.dp))
        Column {
            Text(label, color = HeritageMuted, fontSize = 12.sp)
            Text(value, color = HeritageInk, fontSize = 16.sp, fontWeight = FontWeight.Bold)
        }
    }
}

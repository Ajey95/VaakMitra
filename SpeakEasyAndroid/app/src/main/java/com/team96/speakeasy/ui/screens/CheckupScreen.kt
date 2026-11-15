package com.team96.speakeasy.ui.screens

import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import com.team96.speakeasy.ui.components.*
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.team96.speakeasy.ui.components.AnimatedGradientBackground
import com.team96.speakeasy.ui.components.BouncyButton
import com.team96.speakeasy.ui.theme.GradientWarm
import com.team96.speakeasy.ui.theme.Pink
import com.team96.speakeasy.ui.theme.Purple
import com.team96.speakeasy.ui.navigation.Routes

/** DEC-019/CHK-001..004: reminder UI never invents therapist assignment or appointment. */
@Composable
fun CheckupScreen(nav: NavController) {
    HeritagePage {
        Column(Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(20.dp)) {
            Spacer(Modifier.height(36.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                BackCircle { nav.popBackStack() }
                Column(Modifier.padding(start = 14.dp)) {
                    Text("Therapist checkup", color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 27.sp, fontWeight = FontWeight.Bold)
                    Text("Keep your therapist part of the journey", color = HeritageMuted, fontSize = 13.sp)
                }
            }
            Spacer(Modifier.height(24.dp))
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(28.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(28.dp)).padding(20.dp)) {
                Text("CAREGIVER FOLLOW-UP", color = Color(0xFF6F2338), fontSize = 12.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.1.sp)
                Text("No therapist is linked yet", color = Color(0xFF382726), fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(12.dp))
                Text("You can review the practice log with your therapist and agree on the next checkup. Your child can continue practising at a comfortable pace.", color = Color(0xFF6E5952), lineHeight = 20.sp)
                Spacer(Modifier.height(18.dp))
                Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(Color(0xFFF1E3D5)).padding(14.dp)) {
                    Text("This device has no scheduled appointment. Please arrange follow-up directly with your therapist.", color = Color(0xFF5E473C), fontWeight = FontWeight.Medium, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
                }
            }
            Spacer(Modifier.height(18.dp))
            BouncyButton("View practice progress", listOf(Purple, Pink), modifier = Modifier.fillMaxWidth()) { nav.navigate(Routes.PROGRESS) }
            Spacer(Modifier.height(28.dp))
        }
    }
}

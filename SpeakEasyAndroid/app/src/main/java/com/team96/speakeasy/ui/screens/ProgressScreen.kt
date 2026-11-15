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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import com.team96.speakeasy.ui.components.*
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.ui.components.AnimatedGradientBackground
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.ui.theme.GradientCalm

/** DEC-014/021: progress contains observed event counts only, never difficulty-as-score. */
@Composable
fun ProgressScreen(nav: NavController,report:com.team96.speakeasy.journey.LocalSessionReport?=SessionManager.lastReport) {
    HeritagePage {
        Column(Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(20.dp)) {
            Spacer(Modifier.height(36.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                BackCircle { nav.popBackStack() }
                Column(Modifier.padding(start = 14.dp)) {
                    Text("Practice progress", color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 27.sp, fontWeight = FontWeight.Bold)
                    Text("Your practice journey on this device", color = HeritageMuted, fontSize = 13.sp)
                }
            }
            Spacer(Modifier.height(22.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                EventMetric("Mic tries", report?.attemptCount ?: 0, Modifier.weight(1f))
                EventMetric("Words tried", report?.uniqueWordCount ?: 0, Modifier.weight(1f))
            }
            Spacer(Modifier.height(10.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                EventMetric("Breaks", report?.breakCount ?: 0, Modifier.weight(1f))
                EventMetric("Seconds", report?.durationSeconds?.toInt() ?: 0, Modifier.weight(1f))
            }
            Spacer(Modifier.height(20.dp))
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(24.dp)).padding(18.dp)) {
                Text("Your practice log", color = Color(0xFF382726), fontSize = 19.sp, fontWeight = FontWeight.Bold)
                Text("Every small step counts", color = Color(0xFF6F2338), fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                Text("These totals show participation, breaks and time spent practising. Speech is not graded.", color = Color(0xFF6E5952), lineHeight = 20.sp)
            }
            Spacer(Modifier.height(16.dp))
            Box(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(22.dp))
                    .clickable { nav.navigate(Routes.CHECKUP) }.padding(16.dp),
            ) {
                Column {
                    Text("Fortnightly follow-up", color = HeritageInk, fontWeight = FontWeight.Bold)
                    Text("Review follow-up information with your caregiver.", color = HeritageMuted, fontSize = 13.sp)
                    Text("Open checkup →", color = HeritageInk, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 10.dp))
                }
            }
            Spacer(Modifier.height(28.dp))
        }
    }
}

@Composable
private fun EventMetric(label: String, value: Int, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(22.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(22.dp)).padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value.toString(), color = Color(0xFF6F2338), fontFamily = FontFamily.Serif, fontSize = 28.sp, fontWeight = FontWeight.Bold)
        Text(label, color = Color(0xFF6E5952), fontSize = 12.sp)
    }
}

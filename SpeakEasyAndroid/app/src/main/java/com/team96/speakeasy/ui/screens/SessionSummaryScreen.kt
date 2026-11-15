package com.team96.speakeasy.ui.screens

import androidx.compose.foundation.border
import androidx.compose.foundation.background
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.ui.components.AnimatedGradientBackground
import com.team96.speakeasy.ui.components.BouncyButton
import com.team96.speakeasy.ui.components.GhostButton
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.ui.theme.GradientCalm
import com.team96.speakeasy.ui.theme.Pink
import com.team96.speakeasy.ui.theme.Purple

/** DEC-014/021: event-derived handoff preview with no invented accuracy. */
@Composable
fun SessionSummaryScreen(nav: NavController,report:com.team96.speakeasy.journey.LocalSessionReport?=SessionManager.lastReport,saveStatus:String?=null,vm:com.team96.speakeasy.viewmodel.AppViewModel?=null) {
    HeritagePage {
        Column(
            Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(42.dp))
            Text(if(report==null || (saveStatus!=null && saveStatus!="Saved on this device"))"Session summary" else "Session saved", color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 30.sp, fontWeight = FontWeight.Bold)
            saveStatus?.let{Text(it,color=HeritageMaroon,fontSize=14.sp)}
            Text(if(report==null)"Your next small step can begin whenever you are ready." else "Your practice, at your pace.", color = HeritageMuted)
            Spacer(Modifier.height(22.dp))
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(28.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(28.dp)).padding(20.dp)) {
                Text("PRACTICE LOG", color = Color(0xFF6F2338), fontSize = 13.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp)
                Text(if(report==null) "No session recorded yet" else "Every small step counts", color = Color(0xFF382726), fontSize = 21.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(18.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    SummaryMetric("Duration", "${report?.durationSeconds ?: 0}s", Modifier.weight(1f))
                    SummaryMetric("Mic tries", "${report?.attemptCount ?: 0}", Modifier.weight(1f))
                }
                Spacer(Modifier.height(10.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    SummaryMetric("Words with mic tries", "${report?.uniqueWordCount ?: 0}", Modifier.weight(1f))
                    SummaryMetric("Breaks", "${report?.breakCount ?: 0}", Modifier.weight(1f))
                }
                Spacer(Modifier.height(18.dp))
                if(report!=null && report.activityContextTurns>0){
                    Text("Illustrated examples explored: ${report.activityContextTurns}. These are activity counts, not speech scores.",color=HeritageMuted,fontSize=14.sp,modifier=Modifier.padding(vertical=12.dp))
                }
                if(report!=null && (report.activityChoices>0 || report.activityHelpRequests>0)){
                    Text("Picture practice",color=HeritageMaroon,fontWeight=FontWeight.Bold)
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(10.dp)){
                        SummaryMetric("Picture turns","${report.activityChoices}",Modifier.weight(1f))
                        SummaryMetric("Help requests","${report.activityHelpRequests}",Modifier.weight(1f))
                    }
                    Text("${report.activityMatches} picture matches · ${report.activityWithoutExtraHint} without extra picture hints. These are activity counts, not speech scores.",color=HeritageMuted,fontSize=13.sp,modifier=Modifier.padding(vertical=12.dp))
                }
                Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(Color(0xFFF1E3D5)).padding(14.dp)) {
                    Text("This is a record of practice and participation. Speech is not graded.", color = Color(0xFF5E473C), fontSize = 13.sp, lineHeight = 18.sp)
                }
            }
            Spacer(Modifier.height(18.dp))
            if(vm!=null && com.team96.speakeasy.journey.hasPraiseParticipation(report)){
                EncouragementPanel(vm,com.team96.speakeasy.journey.PraiseEvent.SESSION,heading="Your practice stamp",eventKey=vm.summaryPraiseTicket(report!!.sessionId)?:"historical-summary",automatic=true)
                Spacer(Modifier.height(14.dp))
            }
            BouncyButton("Practice another word", listOf(Purple, Pink), modifier = Modifier.fillMaxWidth()) { nav.navigate(Routes.LESSONS) }
            Spacer(Modifier.height(12.dp))
            GhostButton("Back home", modifier = Modifier.fillMaxWidth()) {
                nav.navigate(Routes.HOME) { popUpTo(Routes.HOME) { inclusive = true } }
            }
            Spacer(Modifier.height(28.dp))
        }
    }
}

@Composable
private fun SummaryMetric(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(18.dp)).background(Color(0xFFEADFD5)).padding(14.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = Purple, fontFamily = FontFamily.Serif, fontSize = 25.sp, fontWeight = FontWeight.Bold)
        Text(label, color = Color(0xFF6E5952), fontSize = 12.sp, textAlign = TextAlign.Center)
    }
}

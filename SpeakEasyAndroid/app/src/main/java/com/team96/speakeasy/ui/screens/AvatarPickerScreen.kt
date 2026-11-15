package com.team96.speakeasy.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.selection.selectable
import androidx.compose.ui.semantics.Role
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
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.Favorite
import androidx.compose.material.icons.rounded.GraphicEq
import androidx.compose.material.icons.rounded.RecordVoiceOver
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import com.team96.speakeasy.ui.components.*
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.heightIn
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.team96.speakeasy.avatar.AvatarId
import com.team96.speakeasy.avatar.AvatarMotion
import com.team96.speakeasy.avatar.AvatarPalette
import com.team96.speakeasy.avatar.AvatarPhase
import com.team96.speakeasy.avatar.AvatarPreference
import com.team96.speakeasy.avatar.AvatarPreferenceStore
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.ui.components.ExpressiveAvatar

private val Ink = Color(0xFF382726)
private val Muted = Color(0xFF6E5952)
private val Teal = Color(0xFF6F2338)
private val Coral = Color(0xFF9A7A63)

/** DEC-026/AVT-001..006: closed, child-scoped companion selection with a live state preview. */
@Composable
fun AvatarPickerScreen(nav: NavController,preview:Boolean=false) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val childScope = if(preview)"public-gallery" else SessionManager.childName
    var draft by remember { mutableStateOf(if(preview)AvatarPreference() else AvatarPreferenceStore.load(context, childScope)) }
    var previewPhase by remember { mutableStateOf(AvatarPhase.IDLE) }
    val motionEnvironment=rememberAvatarMotionEnvironment()
    var greetingKey by remember{mutableStateOf(0)}

    HeritagePage { Column(
        Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp),
    ) {
        Spacer(Modifier.height(28.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            BackCircle { nav.popBackStack() }
            Spacer(Modifier.width(12.dp))
            Column {
                Text("PRACTICE COMPANION", color = Teal, fontSize = 11.sp, fontWeight = FontWeight.Black, letterSpacing = 1.4.sp)
                Text("Choose their guide", color = Ink, fontSize = 27.sp, fontWeight = FontWeight.Black)
            }
        }
        Spacer(Modifier.height(8.dp))
        Text("Pick the character, colours, and amount of movement that feel most comfortable. The practice rules stay the same.", color = Muted, lineHeight = 21.sp)
        Spacer(Modifier.height(18.dp))

        Column(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(28.dp)).background(Brush.verticalGradient(listOf(Color(0xFFF1E3D5), Color(0xFFE8D8CC)))).padding(14.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("LIVE PREVIEW", color = Teal, fontSize = 10.sp, fontWeight = FontWeight.Black, letterSpacing = 1.2.sp)
                Text(draft.avatarId.displayName, color = Coral, fontWeight = FontWeight.Black)
            }
            Text("${draft.motion.displayName} movement",color=Muted,fontSize=12.sp)
            if(!motionEnvironment.systemAnimations)Text("Device animations are off, so this preview stays still.",color=Muted,fontSize=12.sp,textAlign=TextAlign.Center)
            Box(Modifier.fillMaxWidth().padding(top = 10.dp).clip(RoundedCornerShape(18.dp)).background(Color.White).padding(12.dp)) {
                Text(previewMessage(previewPhase), color = Ink, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
            }
            Box(Modifier.fillMaxWidth().height(300.dp), contentAlignment = Alignment.Center) {
                ExpressiveAvatar(draft, previewPhase, speaking = previewPhase == AvatarPhase.PROMPTING, audioLevel = .68f, modifier = Modifier.width(230.dp),greetingKey=greetingKey)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                PreviewChip("Hello", previewPhase == AvatarPhase.IDLE, Modifier.weight(1f)) { previewPhase = AvatarPhase.IDLE;greetingKey++ }
                PreviewChip("Speak", previewPhase == AvatarPhase.PROMPTING, Modifier.weight(1f)) { previewPhase = AvatarPhase.PROMPTING }
                PreviewChip("Listen", previewPhase == AvatarPhase.LISTENING, Modifier.weight(1f)) { previewPhase = AvatarPhase.LISTENING }
                PreviewChip("Cheer", previewPhase == AvatarPhase.PRAISE, Modifier.weight(1f)) { previewPhase = AvatarPhase.PRAISE }
            }
        }

        SectionLabel("1. Pick a guide")
        AvatarId.entries.chunked(2).forEach { row ->
            Row(Modifier.fillMaxWidth().padding(bottom = 9.dp), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                row.forEach { avatar ->
                    val selected = draft.avatarId == avatar
                    Column(
                        Modifier.weight(1f).heightIn(min=188.dp).clip(RoundedCornerShape(20.dp))
                            .background(if (selected) Color(0xFFF4E5E8) else Color.White)
                            .border(if (selected) 2.dp else 1.dp, if (selected) Teal else Color(0xFFD8C7BA), RoundedCornerShape(20.dp))
                            .clickable { draft = draft.copy(avatarId = avatar) }.padding(9.dp),
                    ) {
                        Box(Modifier.fillMaxWidth().height(119.dp).clip(RoundedCornerShape(15.dp)).background(Color(0xFFF7ECE1))) {
                            ExpressiveAvatar(draft.copy(avatarId = avatar, motion = AvatarMotion.STILL), AvatarPhase.IDLE)
                            if (selected) Box(Modifier.align(Alignment.TopEnd).padding(7.dp).size(26.dp).clip(CircleShape).background(Teal), contentAlignment = Alignment.Center) { Icon(Icons.Rounded.Check, null, tint = Color.White, modifier = Modifier.size(17.dp)) }
                        }
                        Text(avatar.displayName, color = Ink, fontWeight = FontWeight.Black, fontSize = 15.sp)
                        Text(avatar.description, color = Muted, fontSize = 11.sp, lineHeight = 13.sp)
                    }
                }
                if (row.size == 1) Spacer(Modifier.weight(1f))
            }
        }

        SectionLabel("2. Choose colours")
        Row(horizontalArrangement = Arrangement.spacedBy(15.dp)) {
            AvatarPalette.entries.forEach { palette -> PaletteButton(palette, draft.palette == palette) { draft = draft.copy(palette = palette) } }
        }

        SectionLabel("3. Set movement")
        Text("Your choice updates the live preview above. Save with Use this guide.",color=Muted,fontSize=12.sp,modifier=Modifier.padding(bottom=10.dp))
        AvatarMotion.entries.forEach { motion ->
            val selected = draft.motion == motion
            Row(
                Modifier.fillMaxWidth().padding(bottom = 8.dp).clip(RoundedCornerShape(16.dp))
                    .background(if (selected) Color(0xFFF4E5E8) else Color.White)
                    .border(1.dp, if (selected) Teal else Color(0xFFD8C7BA), RoundedCornerShape(16.dp))
                    .selectable(selected=selected,role=Role.RadioButton,onClick={draft=draft.copy(motion=motion)}).padding(14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(if (motion == AvatarMotion.STILL) Icons.Rounded.Favorite else if (motion == AvatarMotion.REDUCED) Icons.Rounded.GraphicEq else Icons.Rounded.RecordVoiceOver, null, tint = if (selected) Teal else Coral)
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) { Text(motion.displayName, color = Ink, fontWeight = FontWeight.Black); Text(motion.description, color = Muted, fontSize = 12.sp) }
                if (selected) Icon(Icons.Rounded.Check, null, tint = Teal)
            }
        }

        Spacer(Modifier.height(12.dp))
        Box(
            Modifier.fillMaxWidth().heightIn(min=56.dp).clip(RoundedCornerShape(18.dp)).background(Brush.horizontalGradient(listOf(Color(0xFF6F2338), Color(0xFF8C4053))))
                .clickable {
                    if(!preview)AvatarPreferenceStore.save(context, childScope, draft)
                    val setup=nav.previousBackStackEntry?.takeIf{it.destination.route==com.team96.speakeasy.ui.navigation.Routes.CARE_SETUP}
                    if (setup != null) {
                        if(setup.savedStateHandle.get<Boolean>("initial_learner_setup")==true) {
                            nav.navigate(com.team96.speakeasy.ui.navigation.Routes.HOME) {
                                popUpTo(nav.graph.id) { inclusive = false }
                                launchSingleTop=true
                            }
                        } else nav.popBackStack(com.team96.speakeasy.ui.navigation.Routes.CARE_SETUP,inclusive=true)
                    } else nav.popBackStack()
                },
            contentAlignment = Alignment.Center,
        ) { Row(verticalAlignment = Alignment.CenterVertically) { Icon(Icons.Rounded.Check, null, tint = Color.White); Spacer(Modifier.width(7.dp)); Text("Use this guide", color = Color.White, fontWeight = FontWeight.Black, fontSize = 17.sp) } }
        Text("Saved for this child on this device. No photo or custom upload is needed.", color = Muted, fontSize = 11.sp, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(10.dp))
        Spacer(Modifier.height(24.dp))
    }}
}

@Composable private fun SectionLabel(text: String) { Text(text, color = Ink, fontWeight = FontWeight.Black, fontSize = 17.sp, modifier = Modifier.padding(top = 24.dp, bottom = 10.dp)) }

@Composable private fun PreviewChip(label: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Box(modifier.heightIn(min=48.dp).clip(RoundedCornerShape(14.dp)).background(if (selected) Teal else Color.White.copy(alpha = .85f)).clickable(onClick = onClick), contentAlignment = Alignment.Center) {
        Text(label, color = if (selected) Color.White else Muted, fontSize = 11.sp, fontWeight = FontWeight.Black)
    }
}

@Composable private fun PaletteButton(palette: AvatarPalette, selected: Boolean, onClick: () -> Unit) {
    val colors = when (palette) {
        AvatarPalette.CORAL_TEAL -> listOf(Teal, Color(0xFFF07E6E))
        AvatarPalette.SUNRISE -> listOf(Color(0xFFD86651), Color(0xFFF4BE55))
        AvatarPalette.LOTUS -> listOf(Color(0xFF8B5BB5), Color(0xFFE486A5))
    }
    Box(Modifier.size(58.dp).clip(CircleShape).background(Color.White).border(if (selected) 3.dp else 1.dp, if (selected) Ink else Color(0xFFD8C7BA), CircleShape).padding(5.dp).clip(CircleShape).background(Brush.linearGradient(colors)).clickable(onClick = onClick), contentAlignment = Alignment.Center) {
        if (selected) Icon(Icons.Rounded.Check, palette.displayName, tint = Color.White)
    }
}

private fun previewMessage(phase: AvatarPhase) = when (phase) {
    AvatarPhase.PRAISE -> "Wonderful try! You stayed with the whole word."
    AvatarPhase.LISTENING -> "I’m listening. Take your time."
    AvatarPhase.PROMPTING -> "Listen first, then we’ll say it together."
    else -> "Hello! I’ll practise with you, one step at a time."
}

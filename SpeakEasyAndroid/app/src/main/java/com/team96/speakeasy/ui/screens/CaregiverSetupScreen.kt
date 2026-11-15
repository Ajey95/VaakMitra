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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import com.team96.speakeasy.ui.components.*
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.journey.CarePlan
import com.team96.speakeasy.ui.components.AnimatedGradientBackground
import com.team96.speakeasy.ui.components.BouncyButton
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.ui.theme.GradientCalm
import com.team96.speakeasy.ui.theme.Pink
import com.team96.speakeasy.ui.theme.Purple
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException

/** DEC-020: caregiver-selected pacing, not inferred attention or diagnosis. */
@Composable
fun CaregiverSetupScreen(nav: NavController,preview:Boolean=false) {
    val current = if(preview)CarePlan(childAlias="Sample learner") else SessionManager.carePlan
    val initialSetup=rememberSaveable{!preview && !SessionManager.carePlanConfigured}
    var alias by rememberSaveable { mutableStateOf(current.childAlias) }
    var age by rememberSaveable { mutableStateOf(current.age.toString()) }
    var sessionMinutes by rememberSaveable { mutableIntStateOf(current.sessionMinutes) }
    var focusMinutes by rememberSaveable { mutableIntStateOf(current.focusMinutes) }
    var interest by rememberSaveable { mutableStateOf(current.interest) }
    var saving by rememberSaveable { mutableStateOf(false) }
    var saveError by rememberSaveable { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    HeritagePage {
        Column(
            Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(40.dp))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                if (!preview && SessionManager.carePlanConfigured) BackCircle { nav.popBackStack() }
                Column(Modifier.padding(start = if (SessionManager.carePlanConfigured) 14.dp else 0.dp)) {
                    Text("Build a comfortable plan", color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 27.sp, fontWeight = FontWeight.Bold)
                    Text("Choose the pace that feels comfortable for your child.", color = HeritageMuted, fontSize = 13.sp)
                }
            }
            Spacer(Modifier.height(20.dp))
            Column(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(28.dp)).background(HeritageCard).border(1.dp,HeritageGold,RoundedCornerShape(28.dp)).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                OutlinedTextField(alias, { alias = it.take(30) }, label = { Text("Child nickname") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(
                    age, { age = it.filter(Char::isDigit).take(2) }, label = { Text("Age (7–14)") }, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth(),
                )
                ChoiceRow("Session length", listOf(5, 10, 15, 20), sessionMinutes) { sessionMinutes = it; if(focusMinutes>=it)focusMinutes=2 }
                ChoiceRow("Comfortable focus window", listOf(2, 3, 4, 6, 8).filter { it < sessionMinutes }, focusMinutes) { focusMinutes = it }
                OutlinedTextField(interest, { interest = it.take(40) }, label = { Text("What motivates them? e.g. trains") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Text("Choose a favourite activity",color=HeritageInk,fontWeight=FontWeight.Bold)
                Column(verticalArrangement=Arrangement.spacedBy(6.dp)){
                    for(scene in listOf(com.team96.speakeasy.journey.InterestTheme.TRAINS,com.team96.speakeasy.journey.InterestTheme.ANIMALS,com.team96.speakeasy.journey.InterestTheme.STORIES)){
                        HeritageButton(scene.title,onClick={interest=scene.preference},secondary=com.team96.speakeasy.journey.InterestTheme.fromInterest(interest)!=scene,modifier=Modifier.fillMaxWidth())
                    }
                }
                Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(Color(0xFFF1E3D5)).padding(14.dp)) {
                    Text(
                        "Planned rhythm: $focusMinutes min practice, then a gentle break prompt. The child can always use the red Break / Stop button sooner.",
                        color = Color(0xFF5E473C), fontSize = 13.sp, lineHeight = 18.sp,
                    )
                }
            }
            Spacer(Modifier.height(18.dp))
            saveError?.let{Text(it,color=HeritageInk)}
            BouncyButton(if(saving)"Saving plan…" else "Save plan & choose guide", listOf(Purple, Pink), modifier = Modifier.fillMaxWidth()) {
                if(preview)nav.navigate(Routes.AVATAR_PICKER) else if(!saving)scope.launch {
                    saving=true;saveError=null
                    try {
                        SessionManager.saveCarePlan(CarePlan(alias, age.toIntOrNull() ?: 7, sessionMinutes, focusMinutes, interest))
                        nav.currentBackStackEntry?.savedStateHandle?.set("initial_learner_setup",initialSetup)
                        nav.navigate(Routes.AVATAR_PICKER)
                    } catch(cancelled:CancellationException){throw cancelled}
                    catch(_:Exception){saveError="Couldn't save your plan. Please try again."}
                    finally{saving=false}
                }
            }
            Spacer(Modifier.height(12.dp))
            Text("Stored on this device. No camera or raw audio is used for this plan.", color = HeritageMuted, fontSize = 12.sp, textAlign = TextAlign.Center)
            Spacer(Modifier.height(28.dp))
        }
    }
}

@Composable
@OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
private fun ChoiceRow(label: String, values: List<Int>, selected: Int, onSelect: (Int) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, color = Color(0xFF382726), fontWeight = FontWeight.Bold)
        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            values.forEach { value ->
                Box(
                    Modifier.widthIn(min=64.dp).heightIn(min=56.dp).clip(RoundedCornerShape(14.dp))
                        .background(if (selected == value) Purple else Color(0xFFEADFD5))
                        .clickable { onSelect(value) }.padding(horizontal=12.dp,vertical=12.dp),
                    contentAlignment = Alignment.Center,
                ) { Text("$value min", color = if (selected == value) Color.White else Color(0xFF5E473C), fontSize = 12.sp, fontWeight = FontWeight.Bold) }
            }
        }
    }
}


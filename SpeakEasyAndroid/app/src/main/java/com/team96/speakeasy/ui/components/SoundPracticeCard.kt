package com.team96.speakeasy.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.team96.speakeasy.audio.SoundPracticeCatalog
import com.team96.speakeasy.audio.SoundRecipe
import com.team96.speakeasy.journey.StarterWords
import com.team96.speakeasy.ui.theme.*

/** DEC070/PHN011: host-owned cue state; the learner never selects the next teaching step. */
data class SoundPracticeUiState(val opened:Boolean=true,val step:Int=0)

@Composable
fun SoundPracticeCard(
    recipe:SoundRecipe?,wordId:String,prioritized:Boolean,interactive:Boolean=true,
    state:SoundPracticeUiState,running:Boolean,awaitingAttempt:Boolean,cycleLabel:String?,spokenGuide:Boolean,
    onSkip:()->Unit,onHelp:()->Unit,onPause:()->Unit,
) {
    val word=StarterWords.all.firstOrNull{it.id==wordId}
    val steps=recipe?.let{SoundPracticeCatalog.steps(it,wordId)}.orEmpty()
    val step=if(state.opened && steps.size==3)state.step.coerceIn(0,2)else 2
    val cue=steps.getOrNull(step)?:word?.tamil.orEmpty()
    Column(Modifier.fillMaxWidth().padding(top=10.dp).background(HeritagePaper,RoundedCornerShape(14.dp))
        .border(1.dp,HeritageGold,RoundedCornerShape(14.dp)).padding(12.dp)) {
        Text("ஒலி பயிற்சி · Sound practice",color=HeritageMaroon,fontWeight=FontWeight.Bold,fontSize=16.sp)
        cycleLabel?.let{Text(it,color=HeritageMuted,fontSize=12.sp)}
        Text(if(running)if(spokenGuide)"Listen and join your guide" else "Follow your guide" else if(awaitingAttempt)"உங்கள் முறை · Your turn" else "Practise with your guide",
            color=HeritageInk,fontWeight=FontWeight.Bold,fontSize=15.sp)
        if(running)Text("${step+1} / 3 · ${listOf("Sound","Syllable","Whole word")[step]}",color=HeritageMuted,fontSize=12.sp)
        Text(cue,color=HeritageInk,fontSize=34.sp,textAlign=TextAlign.Center,modifier=Modifier.fillMaxWidth().padding(vertical=8.dp))
        Text(if(running)"Say it with your guide if you like." else "Use the mic when you are ready. You can always pause.",color=HeritageMuted,fontSize=13.sp)
        if(prioritized)Text("A familiar sound to explore together",color=HeritageMuted,fontSize=11.sp)
        if(running)Text(if(spokenGuide)"Voice example" else "Follow the sounds on screen",color=HeritageMuted,fontSize=11.sp)
        val controls:@Composable ()->Unit={
            if(running)TextButton(enabled=interactive,onClick=onSkip){Text("Skip this cue",color=HeritageMaroon)}
            else TextButton(enabled=interactive,onClick=onHelp){Text("Help me practise",color=HeritageMaroon)}
            TextButton(enabled=interactive,onClick=onPause){Text("Pause",color=HeritageMaroon)}
        }
        if(LocalDensity.current.fontScale>1.4f)Column(Modifier.fillMaxWidth()){controls()}
        else Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){controls()}
    }
}

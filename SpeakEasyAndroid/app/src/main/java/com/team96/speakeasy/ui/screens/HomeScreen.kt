package com.team96.speakeasy.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavController
import com.team96.speakeasy.R
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.journey.LetterGroup
import com.team96.speakeasy.journey.TamilAlphabet
import com.team96.speakeasy.ui.components.*
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.viewmodel.AppViewModel

/** DEC-053/054: new letter journey alongside the existing avatar/word-session routes. */
@Composable
fun HomeScreen(nav:NavController,vm:AppViewModel) {
    val context=LocalContext.current
    val stats by vm.stats.collectAsStateWithLifecycle()
    val storedJourney by vm.letterJourney.collectAsStateWithLifecycle()
    val ready by vm.letterReady.collectAsStateWithLifecycle()
    val letterReady=ready && vm.letterIdentityIsCurrent()
    val journey=if(letterReady)storedJourney else com.team96.speakeasy.journey.LetterJourneySnapshot()
    var rhythm by remember { mutableStateOf(false) }
    LaunchedEffect(Unit){vm.loadHome();vm.loadLetterJourney(context)}
    HeritagePage {
        Column(Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(horizontal=20.dp,vertical=14.dp)) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                BrandMark(Modifier.size(42.dp))
                Text("VaakMitra",color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=29.sp,fontWeight=FontWeight.Bold,modifier=Modifier.weight(1f).padding(start=10.dp))
                IconButton(onClick={nav.navigate(Routes.PROFILE)}){Icon(Icons.Rounded.Person,"Profile",tint=HeritageMaroon)}
            }
            Spacer(Modifier.height(12.dp))
            Column(Modifier.fillMaxWidth().border(2.dp,HeritageGold,RoundedCornerShape(9.dp)).clip(RoundedCornerShape(9.dp)).background(HeritageMaroon).padding(horizontal=12.dp,vertical=14.dp),horizontalAlignment=Alignment.CenterHorizontally) {
                Text("எழுத்துப் பயணம்",color=HeritagePaper,fontFamily=FontFamily.Serif,fontWeight=FontWeight.Bold,fontSize=28.sp,lineHeight=38.sp)
                Text("A little practice. A world of Tamil.",color=HeritagePaper.copy(alpha=.92f),fontSize=13.sp)
            }
            Image(painterResource(R.drawable.tamil_thinnai_hero),"Illustrated Tamil veranda with schoolbooks, a slate and a kolam",modifier=Modifier.fillMaxWidth().aspectRatio(2f),contentScale=ContentScale.FillWidth)
            HeritageProgress(journey.progress.completedCount)
            if(!letterReady)Text("Your letter journey isn't ready yet. Try reopening your profile.",color=HeritageMaroon,fontSize=13.sp)
            Spacer(Modifier.height(14.dp))
            val next=journey.progress.nextLetter
            HeritageButton(if(next==null)"Revisit your letter journey" else "Continue learning · ${next.symbol}",onClick={
                if(next==null)nav.navigate(Routes.LESSONS) else nav.navigate("${Routes.LETTER}/${next.id}")
            },enabled=letterReady,modifier=Modifier.fillMaxWidth())
            Spacer(Modifier.height(8.dp))
            HeritageButton("Word practice · ${com.team96.speakeasy.journey.StarterWords.all.size} words",onClick={nav.navigate("${Routes.LESSONS}?section=WORDS")},secondary=true,modifier=Modifier.fillMaxWidth())
            Spacer(Modifier.height(10.dp))
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                Text("First ${journey.settings.roundSize} letters · Then a break",color=HeritageMuted,fontSize=13.sp,modifier=Modifier.weight(1f))
                IconButton(onClick={rhythm=true}){Icon(Icons.Rounded.Settings,"Learning rhythm",tint=HeritageMaroon)}
            }
            Spacer(Modifier.height(10.dp))
            LetterGroup.entries.forEach { group ->
                val letters=TamilAlphabet.inGroup(group)
                val count=letters.count{journey.progress.isPractised(it.id)}
                ChapterRow(group.title,group.tamil,"$count / ${letters.size} practised",onClick={nav.navigate("${Routes.LESSONS}?section=${group.name}")})
                Spacer(Modifier.height(8.dp))
            }
            Spacer(Modifier.height(12.dp))
            Text("Your familiar avatar-led word sessions are always available.",color=HeritageMuted,fontSize=12.sp,modifier=Modifier.padding(top=8.dp,bottom=18.dp))
            ChapterRow("Your guide","உங்கள் துணை","Character & movement",onClick={nav.navigate(Routes.AVATAR_PICKER)})
            Spacer(Modifier.height(8.dp))
            ChapterRow("Caregiver setup","கற்றல் அமைப்பு","${vm.practiceCarePlan.focusMinutes} min blocks · ${vm.practiceCarePlan.sessionMinutes} min sessions",onClick={nav.navigate(Routes.CARE_SETUP)})
            Spacer(Modifier.height(8.dp))
            ChapterRow("Rewards","முயற்சிப் பயணம்","Your recorded account stars",onClick={nav.navigate(Routes.REWARDS)})
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                HeritageButton("Progress",onClick={nav.navigate(Routes.PROGRESS)},secondary=true,modifier=Modifier.weight(1f))
                HeritageButton("Checkup",onClick={nav.navigate(Routes.CHECKUP)},secondary=true,modifier=Modifier.weight(1f))
            }
            Text("${stats.sessions} recorded word sessions · ${stats.completedLessons} words attempted",color=HeritageMuted,fontSize=12.sp,modifier=Modifier.padding(top=16.dp,bottom=6.dp))
            Text("Small steps, at your pace.",color=HeritageMuted,fontSize=11.sp,modifier=Modifier.padding(bottom=20.dp))
        }
    }
    if(rhythm)LearningRhythmDialog(journey.settings,onSave=vm::saveLetterSettings,onDismiss={rhythm=false})
}

@Composable
internal fun ChapterRow(title:String,tamil:String,detail:String,onClick:()->Unit) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).border(1.dp,HeritageWood.copy(alpha=.65f),RoundedCornerShape(10.dp)).clickable(onClick=onClick).padding(horizontal=15.dp,vertical=12.dp),verticalAlignment=Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title,color=HeritageInk,fontFamily=FontFamily.Serif,fontWeight=FontWeight.Bold,fontSize=21.sp)
            Text(tamil,color=HeritageMaroon,fontSize=15.sp)
        }
        Column(horizontalAlignment=Alignment.End,modifier=Modifier.weight(.75f)) {
            Text(detail,color=HeritageMuted,fontSize=12.sp)
            Text("›",color=HeritageMaroon,fontSize=23.sp)
        }
    }
}

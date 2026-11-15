package com.team96.speakeasy.ui.screens

import android.os.SystemClock
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.team96.speakeasy.avatar.AvatarPhase
import com.team96.speakeasy.avatar.AvatarPreferenceStore
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.journey.*
import com.team96.speakeasy.ui.components.*
import kotlinx.coroutines.delay

/** DEC-053/054/056: letter pacing wraps the same voice session; manual participation only. */
@Composable
fun LetterLearningScreen(
    letterId:String,onBack:()->Unit,journey:LetterJourneySnapshot=LetterJourneySnapshot(),
    ready:Boolean=true,onPracticeComplete:(String)->Boolean={false},
    nav:androidx.navigation.NavController,vm:com.team96.speakeasy.viewmodel.AppViewModel,
    scopeKey:String="isolated-preview",
) {
    BindPraiseBackground(vm)
    val praiseOrigin=remember(scopeKey,letterId){vm.wordIdentity()}
    if(!ready){HeritagePage{Column(Modifier.safeDrawingPadding().padding(20.dp)){HeritageHeading("Letter progress unavailable","Return to your journey or sign in again to identify your account.",onBack)}};return}
    var activeId by rememberSaveable(scopeKey,letterId){mutableStateOf(letterId)}
    var confirmedCount by rememberSaveable(scopeKey,letterId){mutableIntStateOf(journey.progress.completedCount)}
    val progress=LetterProgress.restore(maxOf(confirmedCount,journey.progress.completedCount))
    val letter=TamilAlphabet.find(activeId)
    if(letter==null || !progress.canOpen(activeId)){
        HeritagePage{Column(Modifier.fillMaxSize().safeDrawingPadding().padding(20.dp)){
            HeritageHeading(if(letter==null)"Letter unavailable" else "Level locked",if(letter==null)"Return to your letter journey." else "Practise the earlier levels to open this letter.",onBack)
            Spacer(Modifier.height(32.dp));KolamMark(Modifier.size(80.dp).align(Alignment.CenterHorizontally))
        }};return
    }
    val context=LocalContext.current
    val preference=remember(context,vm.guideScope){vm.guidePreference(context)}
    val plan=vm.practiceCarePlan
    val sessionSaver=remember{listSaver<LetterSession,Long>(save={it.snapshot()},restore={LetterSession.restore(it)})}
    var session by rememberSaveable(scopeKey,letterId,stateSaver=sessionSaver){mutableStateOf(LetterSession.start(journey.settings.roundSize,plan.focusMinutes*60000L,plan.sessionMinutes*60000L))}
    val initialCount=rememberSaveable(scopeKey,letterId){journey.progress.completedCount}
    var showSummary by rememberSaveable(scopeKey,letterId){mutableStateOf(false)}
    var resetTrace by remember{mutableIntStateOf(0)}
    var pendingNextId by rememberSaveable(scopeKey,letterId){mutableStateOf<String?>(null)}
    var terminalRound by rememberSaveable(scopeKey,letterId){mutableStateOf(false)}
    var error by remember{mutableStateOf(false)}
    var confirming by remember(activeId){mutableStateOf(false)}
    var hasPracticeMark by rememberSaveable(scopeKey,letterId){mutableStateOf(false)}
    var praiseSerial by rememberSaveable(scopeKey,letterId){mutableIntStateOf(0)}
    var praisePending by rememberSaveable(scopeKey,letterId){mutableStateOf(false)}
    var practiceTurns by rememberSaveable(scopeKey,letterId){mutableIntStateOf(0)}
    var praiseTicket by remember(scopeKey,letterId){mutableStateOf<String?>(null)}
    var summaryTicket by remember(scopeKey,letterId){mutableStateOf<String?>(null)}
    val lifecycle=LocalLifecycleOwner.current.lifecycle
    DisposableEffect(lifecycle){
        val observer=LifecycleEventObserver{_,event->if(event==Lifecycle.Event.ON_PAUSE){vm.cancelPraise(praiseTicket);vm.cancelPraise(summaryTicket);praiseTicket=null;summaryTicket=null;praisePending=false;resetTrace++;session=session.pause(LetterPause.BACKGROUND)}}
        lifecycle.addObserver(observer);onDispose{lifecycle.removeObserver(observer)}
    }
    LaunchedEffect(Unit){
        var previous=SystemClock.elapsedRealtime()
        while(true){delay(500);val now=SystemClock.elapsedRealtime();if(lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))session=session.tick(now-previous);previous=now}
    }
    LaunchedEffect(activeId){resetTrace++;error=false}
    fun endSession(){vm.cancelPraise(praiseTicket);praiseTicket=null;summaryTicket=if(practiceTurns>0 && journey.settings.rewardsEnabled)vm.issuePraise(praiseOrigin)else null;resetTrace++;session=session.pause();showSummary=true}
    BackHandler{if(showSummary)onBack()else endSession()}
    if(showSummary){
        HeritagePage{Column(Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp),horizontalAlignment=Alignment.CenterHorizontally){
            HeritageHeading("A little learning, together","இன்றைய பயிற்சி",onBack)
            Spacer(Modifier.height(26.dp));ExpressiveAvatar(preference,AvatarPhase.IDLE,modifier=Modifier.width(140.dp).height(130.dp))
            Text("Your practice is saved.",color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=28.sp,textAlign=TextAlign.Center)
            Spacer(Modifier.height(16.dp));Text("${(progress.completedCount-initialCount).coerceAtLeast(0)} new letter practice marks",color=HeritageMaroon,fontSize=18.sp)
            Text("Rest is part of learning. Return when you are ready.",color=HeritageMuted,fontSize=16.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(vertical=22.dp))
            if(practiceTurns>0 && journey.settings.rewardsEnabled)EncouragementPanel(vm,PraiseEvent.SESSION,heading="Your practice stamp",eventKey=summaryTicket?:"restored-letter-summary",automatic=true)
            HeritageButton("Back to your journey",onBack,modifier=Modifier.fillMaxWidth())
            Text("Participation only · not pronunciation or attention scores",color=HeritageMuted,fontSize=12.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(top=16.dp))
        }};return
    }
    if(session.paused){
        val next=if(terminalRound)null else (pendingNextId?.let{TamilAlphabet.find(it)} ?: letter)
        HeritagePage{Column(Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp),horizontalAlignment=Alignment.CenterHorizontally){
            Spacer(Modifier.height(24.dp));KolamMark(Modifier.size(110.dp))
            ExpressiveAvatar(preference,AvatarPhase.BREAK,modifier=Modifier.width(120.dp).height(110.dp))
            Spacer(Modifier.height(12.dp))
            Text(if(session.ended)"A good time to finish." else "Take your time.",color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=32.sp,textAlign=TextAlign.Center)
            Text(if(session.ended)"Your planned session time is complete." else "Ready when you are.",color=HeritageMuted,fontSize=19.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(vertical=16.dp))
            if(session.reason==LetterPause.ROUND)Text("${session.roundPractised} practice marks · a moment to rest",color=HeritageMaroon,textAlign=TextAlign.Center)
            if(earnedPraiseRound(session.reason,session.roundPractised,session.roundSize) && journey.settings.rewardsEnabled)EncouragementPanel(vm,PraiseEvent.ROUND,heading="Your round stamp",eventKey=praiseTicket?:"restored-letter-round",automatic=true)
            if(!session.ended && next!=null)Text("When you continue: ${next.symbol}",color=HeritageMuted,modifier=Modifier.padding(vertical=20.dp))
            Spacer(Modifier.height(28.dp))
            if(!session.ended && next!=null)HeritageButton("Continue when ready",onClick={vm.cancelPraise(praiseTicket);praiseTicket=null;praisePending=false;activeId=next.id;pendingNextId=null;session=session.resume()},modifier=Modifier.fillMaxWidth())
            Spacer(Modifier.height(12.dp));HeritageButton("End session",onClick={endSession()},secondary=true,modifier=Modifier.fillMaxWidth())
            Text("Your progress stays. There is no hurry.",color=HeritageMuted,fontSize=13.sp,modifier=Modifier.padding(top=18.dp),textAlign=TextAlign.Center)
        }};return
    }
    fun confirmPractice() {
        if(session.paused || confirming)return
        confirming=true
        if(!progress.isPractised(activeId)) {
            if(!onPracticeComplete(activeId)){confirming=false;error=true;return}
            confirmedCount=progress.complete(activeId).completedCount
        }
        hasPracticeMark=true
        praiseSerial++;praisePending=true;practiceTurns++;praiseTicket=if(journey.settings.rewardsEnabled)vm.issuePraise(praiseOrigin)else null
        session=session.practice()
        val updated=LetterProgress.restore(maxOf(confirmedCount,journey.progress.completedCount))
        val next=nextLetterVoiceTarget(activeId,updated)
        if(next==null){
            if(earnedPraiseRound(session.reason,session.roundPractised,session.roundSize)){terminalRound=true;pendingNextId=null}
            else endSession()
            return
        }
        if(session.paused)pendingNextId=next.id else activeId=next.id
    }
    Box(Modifier.fillMaxSize()) {
        PracticeScreen(
            nav,vm,lessonId=0,letterTarget=letter,
            onLetterComplete={confirmPractice()},onLetterExit={endSession()},
            onLetterBreak={vm.cancelPraise(praiseTicket);praiseTicket=null;praisePending=false;session=session.pause()},
            letterRoundLabel="First practise · Then a break · ${session.roundPractised} / ${session.roundSize}",
            letterPracticeMark=hasPracticeMark && journey.settings.rewardsEnabled,
            letterPraiseSerial=if(praisePending)praiseSerial else 0,
            letterPraiseTicket=praiseTicket,
            letterRewardsEnabled=journey.settings.rewardsEnabled,
            onLetterAttempt={practiceTurns=(practiceTurns+1).coerceAtMost(10000)},
        )
        if(error)Text("Practice could not be saved. Please try again.",color=HeritageMaroon,
            modifier=Modifier.align(Alignment.TopCenter).safeDrawingPadding().padding(top=92.dp))
    }
}

package com.team96.speakeasy.ui.screens

import android.Manifest
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontFamily
import com.team96.speakeasy.ui.components.HeritagePage
import com.team96.speakeasy.ui.components.HeritageHeading
import com.team96.speakeasy.ui.components.HeritagePaper
import com.team96.speakeasy.ui.components.HeritageInk
import com.team96.speakeasy.ui.components.HeritageMaroon
import com.team96.speakeasy.ui.components.HeritageWood
import com.team96.speakeasy.ui.components.HeritageGold
import com.team96.speakeasy.ui.components.HeritageMuted
import com.team96.speakeasy.ui.components.HeritageSlate
import com.team96.speakeasy.ui.components.HeritageButton
import com.team96.speakeasy.ui.components.KolamMark

import android.content.pm.PackageManager
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.team96.speakeasy.audio.PracticeAudioBoundary
import com.team96.speakeasy.audio.AsyncResourceOwner
import kotlinx.coroutines.CancellationException
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.scaleIn
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.VolumeUp
import androidx.compose.material.icons.rounded.Mic
import androidx.compose.material.icons.rounded.Stop
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.key
import androidx.compose.runtime.saveable.Saver
import com.team96.speakeasy.journey.SessionTally
import com.team96.speakeasy.journey.WordProgressCodec
import com.team96.speakeasy.journey.pictureProgressWithSupport
import com.team96.speakeasy.journey.choosePictureWithSupport
import com.team96.speakeasy.journey.wordIdlePrompt
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.saveable.listSaver
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.navigation.NavController
import com.team96.speakeasy.BuildConfig
import com.team96.speakeasy.avatar.AvatarPhase
import com.team96.speakeasy.avatar.AvatarPreferenceStore
import com.team96.speakeasy.audio.LocalWordPractice
import com.team96.speakeasy.audio.LocalTamilSpeaker
import com.team96.speakeasy.audio.SpeechReadiness
import com.team96.speakeasy.audio.AttemptGeneration
import com.team96.speakeasy.audio.MobileWordPracticeEngine
import com.team96.speakeasy.audio.PracticeMicrophone
import com.team96.speakeasy.audio.SoundPracticePolicy
import com.team96.speakeasy.audio.SoundPracticeCatalog
import com.team96.speakeasy.audio.SoundPracticeTracker
import com.team96.speakeasy.audio.runGuideCues
import com.team96.speakeasy.audio.GuideCadence
import com.team96.speakeasy.audio.SoundRecipe
import com.team96.speakeasy.audio.PracticeVoiceCoach
import com.team96.speakeasy.audio.PauseAlignmentResult
import com.team96.speakeasy.audio.runCoachPreface
import com.team96.speakeasy.journey.AutonomousPracticePolicy
import com.team96.speakeasy.journey.AutonomousPracticeState
import com.team96.speakeasy.journey.WordCycleSignal
import com.team96.speakeasy.ui.components.SoundPracticeCard
import com.team96.speakeasy.ui.components.SoundPracticeUiState
import com.team96.speakeasy.audio.WordPracticePresentation
import com.team96.speakeasy.ui.components.AnimatedGradientBackground
import com.team96.speakeasy.ui.components.BouncyButton
import com.team96.speakeasy.ui.components.ExpressiveAvatar
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.journey.TamilLetter
import com.team96.speakeasy.journey.TamilAlphabet
import com.team96.speakeasy.journey.LetterGroup
import com.team96.speakeasy.journey.letterVoiceLesson
import com.team96.speakeasy.ui.components.LetterTraceSlate
import com.team96.speakeasy.journey.SessionEvent
import com.team96.speakeasy.journey.StarterWords
import com.team96.speakeasy.journey.nextStarterLessonId
import com.team96.speakeasy.journey.summarizeSession
import com.team96.speakeasy.journey.InterestTheme
import com.team96.speakeasy.journey.PictureProgress
import com.team96.speakeasy.journey.PromptHelp
import com.team96.speakeasy.journey.WordLearningPacing
import com.team96.speakeasy.journey.LetterSession
import com.team96.speakeasy.journey.LetterPause
import com.team96.speakeasy.journey.adaptiveWordLessonId
import com.team96.speakeasy.journey.pictureSelection
import com.team96.speakeasy.ui.components.InterestLearningCard
import com.team96.speakeasy.ui.components.EncouragementPanel
import com.team96.speakeasy.journey.PraiseEvent
import com.team96.speakeasy.journey.roundParticipationSnapshot
import com.team96.speakeasy.journey.restoreRoundParticipation
import com.team96.speakeasy.journey.PraiseStyle
import com.team96.speakeasy.journey.SessionFinishGate
import com.team96.speakeasy.journey.hasPraiseParticipation
import com.team96.speakeasy.journey.hasRecordedSamples
import com.team96.speakeasy.journey.recordedPraiseEligible
import com.team96.speakeasy.journey.earnedPraiseRound
import com.team96.speakeasy.ui.components.BindPraiseBackground
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.ui.theme.GradientWarm
import com.team96.speakeasy.ui.theme.LessonColors
import com.team96.speakeasy.ui.theme.Pink
import com.team96.speakeasy.ui.theme.Purple
import com.team96.speakeasy.viewmodel.AppViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private enum class Phase { IDLE, PREPARING, RECORDING, PROCESSING, RESULT, PAUSED }
private enum class GuidePurpose { INTRO, FEEDBACK }
private data class GuideRequest(val purpose:GuidePurpose,val lessonId:Int,val ticket:Long,val manualSpeech:Boolean=false)

/** DEC-013/FUS-007/UX-003: word attempts stay on device and never display an invented score. */
@Composable
fun PracticeScreen(
    nav:NavController,vm:AppViewModel,lessonId:Int,letterTarget:TamilLetter?=null,
    onLetterComplete:(()->Unit)?=null,onLetterExit:(()->Unit)?=null,onLetterBreak:(()->Unit)?=null,
    letterRoundLabel:String?=null,letterPracticeMark:Boolean=false,focusedWords:Boolean=false,
    publicPreviewOutcome:com.team96.speakeasy.audio.LocalWordOutcome?=null,
    letterPraiseSerial:Int=0,
    letterPraiseTicket:String?=null,
    letterRewardsEnabled:Boolean=true,onLetterAttempt:(()->Unit)?=null,
    publicPreviewCompletedTurns:Int=0,
    publicPreviewAutonomous:Boolean=false,
) {
    BindPraiseBackground(vm)
    // ILR011: a different identity gets a different restoration namespace.
    key(vm.wordIdentity()){
        PracticeSession(nav,vm,lessonId,letterTarget,onLetterComplete,onLetterExit,onLetterBreak,letterRoundLabel,letterPracticeMark,focusedWords,publicPreviewOutcome,letterPraiseSerial,letterPraiseTicket,letterRewardsEnabled,onLetterAttempt,publicPreviewCompletedTurns,publicPreviewAutonomous)
    }
}

@Composable
private fun PracticeSession(
    nav: NavController, vm: AppViewModel, lessonId: Int,
    letterTarget: TamilLetter? = null,
    onLetterComplete: (() -> Unit)? = null,
    onLetterExit: (() -> Unit)? = null,
    onLetterBreak: (() -> Unit)? = null,
    letterRoundLabel: String? = null,
    letterPracticeMark: Boolean = false,
    focusedWords: Boolean = false,
    publicPreviewOutcome: com.team96.speakeasy.audio.LocalWordOutcome? = null,
    letterPraiseSerial:Int=0,
    letterPraiseTicket:String?=null,
    letterRewardsEnabled:Boolean=true,onLetterAttempt:(()->Unit)?=null,
    publicPreviewCompletedTurns:Int=0,
    publicPreviewAutonomous:Boolean=false,
) {
    val context = LocalContext.current
    val lessonScroll = rememberScrollState()
    val learningIdentity=vm.wordIdentity()
    var activeLessonId by rememberSaveable(lessonId,learningIdentity) { mutableStateOf(lessonId) }
    val lesson = if (letterTarget != null) letterVoiceLesson(letterTarget.id) else vm.lessonById(activeLessonId)
    val isPublicPreview=vm.isPublicPreview
    val initialPreview=publicPreviewOutcome.takeIf { BuildConfig.DEBUG && isPublicPreview }
    // Old public fixtures remain inert; only explicit debug fixtures seed an automatic result.
    val autonomous=letterTarget==null && (!isPublicPreview || (BuildConfig.DEBUG && publicPreviewAutonomous))
    // Inert debug fixtures only; a learner session cannot seed completed turns.
    val previewCompletedTurns=if(initialPreview!=null)publicPreviewCompletedTurns.coerceIn(0,2)else 0
    val avatarPreference = remember(context, vm.guideScope) { vm.guidePreference(context) }
    val observedWordProgress by vm.wordProgress.collectAsStateWithLifecycle()
    val pictureSaver=remember{Saver<Map<String,PictureProgress>,String>(save={WordProgressCodec.encode(it)},restore={WordProgressCodec.decode(it)})}
    var sessionPictures by rememberSaveable(learningIdentity,stateSaver=pictureSaver){mutableStateOf<Map<String,PictureProgress>>(emptyMap())}
    val observedWordReady by vm.wordReady.collectAsStateWithLifecycle()
    val wordReady=observedWordReady && vm.wordReadyForCurrent()
    val wordProgress=(if(vm.canShowWordHistory)observedWordProgress else emptyMap())+sessionPictures
    val carePlan=vm.practiceCarePlan
    val clockSaver=remember{listSaver<LetterSession,Long>(save={it.snapshot()},restore={WordLearningPacing.restore(it)})}
    var wordClock by rememberSaveable(learningIdentity,lessonId,carePlan.focusMinutes,carePlan.sessionMinutes,stateSaver=clockSaver){mutableStateOf(WordLearningPacing.start(carePlan).let{it.copy(roundPractised=previewCompletedTurns.coerceAtMost(it.roundSize-1))})}
    var interestScene by rememberSaveable(learningIdentity,carePlan.interest){mutableStateOf(InterestTheme.fromInterest(carePlan.interest).name)}
    var turnIndex by rememberSaveable(learningIdentity,lessonId){mutableStateOf(0)}
    var pictureFeedback by rememberSaveable(learningIdentity,lessonId){mutableStateOf<Boolean?>(null)}
    var partsOpen by rememberSaveable(learningIdentity,lessonId){mutableStateOf(false)}
    var contextExplored by rememberSaveable(learningIdentity,lessonId){mutableStateOf(false)}
    var extraSupportUsed by rememberSaveable(learningIdentity,lessonId){mutableStateOf(false)}
    var markedTurn by rememberSaveable(learningIdentity,lessonId){mutableStateOf(false)}
    var praiseSerial by rememberSaveable(learningIdentity,lessonId){mutableStateOf(0)}
    var praiseCue by rememberSaveable(learningIdentity,lessonId){mutableStateOf<String?>(null)}
    var praiseTicket by remember(learningIdentity,lessonId){mutableStateOf<String?>(null)}
    var roundPraiseTicket by remember(learningIdentity,lessonId){mutableStateOf<String?>(null)}
    var handoffTicket by remember(learningIdentity,lessonId){mutableStateOf<String?>(null)}
    val participationSaver=remember{Saver<Int,Any>(save={roundParticipationSnapshot(it)},restore={restoreRoundParticipation(it)})}
    var roundParticipation by rememberSaveable(learningIdentity,lessonId,stateSaver=participationSaver){mutableStateOf(previewCompletedTurns)}
    var turnParticipation by rememberSaveable(learningIdentity,lessonId){mutableStateOf(initialPreview!=null)}
    var terminalRound by rememberSaveable(learningIdentity,lessonId){mutableStateOf(false)}
    var settledLetterId by remember{mutableStateOf<String?>(null)}
    var pendingNextId by rememberSaveable(learningIdentity,lessonId){mutableStateOf<Int?>(null)}
    var learningWritePending by remember{mutableStateOf(false)}
    var previousIdentity by remember{mutableStateOf(learningIdentity)}
    var scrollTarget by remember{mutableStateOf(activeLessonId)}

    val recorder = remember { PracticeMicrophone() }
    // DEC069: core learning flow; transient patterns never become child history or diagnoses.
    val soundTracker = remember { SoundPracticeTracker() }
    var soundRevision by remember { mutableStateOf(0) }
    var soundUiState by remember(activeLessonId) { mutableStateOf(SoundPracticeUiState()) }
    var practiceReferences by remember { mutableStateOf<Map<String,List<String>>>(emptyMap()) }
    var voiceCoachCue by remember(activeLessonId){mutableStateOf(initialPreview?.coachCue)}
    var coachAlignment by remember(activeLessonId){mutableStateOf<PauseAlignmentResult?>(null)}
    var displayedGuideRecipe by remember(activeLessonId){mutableStateOf<SoundRecipe?>(null)}
    var cycleState by remember(lessonId,focusedWords,carePlan.focusMinutes){mutableStateOf(AutonomousPracticePolicy.start(lessonId,focusedWords,carePlan.focusMinutes))}
    var cycleSignal by remember { mutableStateOf(if(autonomous&&initialPreview!=null)WordCycleSignal(
        initialPreview.reason=="PHONEME_TOKENS",initialPreview.soundPracticeEvidence?.sequenceAgrees==true)else null) }
    var childRequestedHelp by remember(activeLessonId){mutableStateOf(false)}
    val cueGeneration=remember{AttemptGeneration()}
    var guideRequest by remember { mutableStateOf<GuideRequest?>(null) }
    var guideRunning by remember { mutableStateOf(false) }
    var awaitingAttempt by remember { mutableStateOf(false) }
    var automaticRoundAllowed by remember { mutableStateOf(false) }
    var roundStartedAt by remember { mutableStateOf(0L) }
    var roundForegroundCharge by remember { mutableStateOf(0L) }
    val scope = rememberCoroutineScope()
    var phase by remember { mutableStateOf(if(initialPreview==null)Phase.IDLE else Phase.RESULT) }
    var presentation by remember { mutableStateOf<WordPracticePresentation?>(initialPreview?.let{LocalWordPractice.present(it)}) }
    var lastDevelopmentResult by remember { mutableStateOf(initialPreview?.developmentResult) }
    var errorMsg by remember { mutableStateOf<String?>(null) }
    var engine by remember { mutableStateOf<MobileWordPracticeEngine?>(null) }
    var isSpeaking by remember { mutableStateOf(false) }
    var finishing by remember { mutableStateOf(false) }
    val finishGate=remember(learningIdentity){SessionFinishGate(learningIdentity)}
    var attemptHasSamples by remember { mutableStateOf(initialPreview!=null) }
    val speaker = remember(context,isPublicPreview) { if(isPublicPreview)null else LocalTamilSpeaker(context,onUnavailable={errorMsg="The offline Tamil voice is unavailable. You can practise without it."}) { isSpeaking = it } }
    val startedAt = rememberSaveable(learningIdentity) { System.currentTimeMillis() }
    val sessionId = rememberSaveable(learningIdentity) { "LOCAL-${System.currentTimeMillis()}" }
    val tallySaver=remember{Saver<SessionTally,String>(save={it.encode()},restore={SessionTally.decode(it)})}
    var tally by rememberSaveable(learningIdentity,stateSaver=tallySaver){mutableStateOf(SessionTally())}
    val attemptGeneration = remember { AttemptGeneration() }
    val engineOwner = remember { AsyncResourceOwner<MobileWordPracticeEngine>(com.team96.speakeasy.audio.ModelResourceRelease::dispatch) }
    val audioBoundary = remember { PracticeAudioBoundary({
        if(roundStartedAt>0){roundForegroundCharge+=(android.os.SystemClock.elapsedRealtime()-roundStartedAt).coerceAtLeast(0);roundStartedAt=0}
        attemptGeneration.invalidate();cueGeneration.invalidate();guideRequest=null;guideRunning=false;automaticRoundAllowed=false
    },{recorder.cancel()},{speaker?.stop()}) }
    var pendingPermission by remember { mutableStateOf<Long?>(null) }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var lifecycleResumed by remember{mutableStateOf(lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))}
    fun cancelGuidance(){cueGeneration.invalidate();guideRequest=null;guideRunning=false;displayedGuideRecipe=null;speaker?.stop()}
    fun requestGuide(purpose:GuidePurpose,manualSpeech:Boolean=false){
        if(!autonomous || finishing || wordClock.paused || !lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))return
        cancelGuidance();awaitingAttempt=false;guideRunning=true
        guideRequest=GuideRequest(purpose,activeLessonId,cueGeneration.next(),manualSpeech)
    }

    LaunchedEffect(context) {
        practiceReferences=withContext(Dispatchers.IO){MobileWordPracticeEngine.loadPracticePhones(context)}
    }

    DisposableEffect(lifecycle) {
        val stateObserver=LifecycleEventObserver { _,event ->
            if(event==Lifecycle.Event.ON_RESUME)lifecycleResumed=true
            if(event==Lifecycle.Event.ON_PAUSE){
                lifecycleResumed=false
                vm.cancelPraise(praiseTicket);praiseTicket=null
                vm.cancelPraise(roundPraiseTicket);roundPraiseTicket=null;vm.cancelPraise(handoffTicket);handoffTicket=null
                presentation=null
                if(letterTarget==null)wordClock=wordClock.pause(LetterPause.BACKGROUND)
                phase=if(letterTarget==null)Phase.PAUSED else Phase.IDLE
            }
        }
        lifecycle.addObserver(audioBoundary)
        lifecycle.addObserver(stateObserver)
        onDispose{lifecycle.removeObserver(audioBoundary);lifecycle.removeObserver(stateObserver)}
    }

    LaunchedEffect(context,learningIdentity){
        if(letterTarget==null){
            if(previousIdentity!=learningIdentity){
                audioBoundary.background();presentation=null;lastDevelopmentResult=null;phase=Phase.PAUSED
                wordClock=wordClock.pause(LetterPause.BACKGROUND);previousIdentity=learningIdentity
            }
            withContext(Dispatchers.IO){vm.loadWordLearning(context)}
        }
    }
    LaunchedEffect(letterTarget?.id){
        if(letterTarget==null){
            var previous=android.os.SystemClock.elapsedRealtime()
            while(true){delay(500);val now=android.os.SystemClock.elapsedRealtime();if(lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))wordClock=wordClock.tick(now-previous);previous=now}
        }
    }
    LaunchedEffect(wordClock.reason){
        if(letterTarget==null && wordClock.paused){
            if(wordClock.reason in setOf(LetterPause.ROUND,LetterPause.FOCUS,LetterPause.SUPPORT))tally=tally.record(SessionEvent.Break)
            audioBoundary.background();presentation=null;phase=Phase.PAUSED
            if(autonomous && wordClock.reason==LetterPause.ROUND && pendingNextId!=null && lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)){
                roundForegroundCharge=0;roundStartedAt=android.os.SystemClock.elapsedRealtime();automaticRoundAllowed=true
            }
        }
    }
    LaunchedEffect(activeLessonId){if(letterTarget==null && scrollTarget!=activeLessonId){lessonScroll.scrollTo(0);scrollTarget=activeLessonId}}

    // DEC-028/MST-006: all assets are verified before the first capture is accepted.
    LaunchedEffect(Unit) {
        if (BuildConfig.DEBUG && !isPublicPreview) {
            val loaded = runCatching { engineOwner.load { MobileWordPracticeEngine.create(context, enabled = true) } }
            loaded.exceptionOrNull()?.let { if(it is CancellationException)throw it }
            engine = loaded.getOrNull()
            if (engine == null) errorMsg = "Sound feedback is unavailable right now. You can still explore the example."
        }
    }

    fun countWordTurn(participated:Boolean){
        if(wordClock.paused)return
        if(participated)roundParticipation=(roundParticipation+1).coerceAtMost(wordClock.roundSize)
        wordClock=wordClock.practice()
        if(earnedPraiseRound(wordClock.reason,roundParticipation,wordClock.roundSize))roundPraiseTicket=vm.issuePraise(learningIdentity)
    }
    fun finishSession() {
        if(!finishGate.begin(vm.wordIdentity()))return
        finishing=true
        vm.cancelPraise(praiseTicket);praiseTicket=null
        audioBoundary.close()
        if (letterTarget != null) { onLetterExit?.invoke(); return }
        val report=tally.report(sessionId,startedAt,System.currentTimeMillis())
        val prepared=if(hasPraiseParticipation(report)&&lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))vm.issuePraise(learningIdentity)else null
        handoffTicket=prepared
        scope.launch {
            vm.savePracticeReport(report,learningIdentity,prepared)
            if(vm.wordIdentity()!=learningIdentity)return@launch
            handoffTicket=null // transfer to summary; actual Activity background still invalidates it
            vm.loadHome()
            nav.navigate(Routes.SUMMARY) { popUpTo(Routes.PRACTICE) { inclusive = true } }
        }
    }

    fun resetPictureTurn(){vm.cancelPraise(praiseTicket);praiseTicket=null;turnParticipation=false;turnIndex++;pictureFeedback=null;partsOpen=false;markedTurn=false;contextExplored=false;extraSupportUsed=false;praiseCue=null}
    fun praise(event:PraiseEvent){praiseSerial++;praiseCue=event.name;praiseTicket=if(letterTarget==null&&wordClock.paused)null else vm.issuePraise(learningIdentity)}
    fun speakPraise(style:PraiseStyle,event:PraiseEvent):Boolean {
        if(finishing || guideRunning || vm.wordIdentity()!=learningIdentity || !lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED) || phase==Phase.PREPARING || phase==Phase.RECORDING || phase==Phase.PROCESSING)return false
        if(phase!=Phase.PAUSED && !audioBoundary.isForeground)return false
        if(phase==Phase.IDLE && letterTarget==null && wordClock.paused)return false
        return speaker?.speakPraise(vm.praiseName,style,event)==true
    }
    fun nextPracticeLesson():Int? {
        val sound=soundTracker.prioritizedSound()
        val related=sound?.let{recipe->SoundPracticePolicy.relatedLesson(activeLessonId,focusedWords,
            practiceReferences.filterValues{recipe.token in it}.keys)}
        return related ?: adaptiveWordLessonId(activeLessonId,focusedWords,wordProgress)
    }
    fun moveToWord(next:Int?){
        cancelGuidance()
        vm.cancelPraise(praiseTicket);praiseTicket=null
        attemptGeneration.invalidate();recorder.cancel();speaker?.stop();presentation=null;lastDevelopmentResult=null
        if(!markedTurn)countWordTurn(turnParticipation)
        if(next==null&&!earnedPraiseRound(wordClock.reason,roundParticipation,wordClock.roundSize)){finishSession();return}
        if(wordClock.paused){pendingNextId=next;terminalRound=next==null;phase=Phase.PAUSED;audioBoundary.background()}
        else if(next!=null){terminalRound=false;activeLessonId=next;resetPictureTurn();phase=Phase.IDLE}
    }
    fun requestActivityHelp(){
        if(letterTarget!=null || (phase!=Phase.IDLE && phase!=Phase.RESULT))return
        val id=StarterWords.byNumericLessonId(activeLessonId)?.id ?: return
        extraSupportUsed=true
        childRequestedHelp=true
        tally=tally.record(SessionEvent.PictureHelp(id))
        if(learningWritePending || !wordReady)return
        val shown=(wordProgress[id]?:PictureProgress()).requestedHelp(java.time.LocalDate.now().toEpochDay())
        sessionPictures=sessionPictures+(id to shown)
        learningWritePending=true
        scope.launch{
            try{val ok=withContext(Dispatchers.IO){vm.recordWordProgress(learningIdentity,id,shown)};if(!ok)errorMsg="This turn could not be saved. You can keep practising."}
            finally{learningWritePending=false}
        }
    }

    fun advanceFromWord(){
        if(!autonomous){moveToWord(nextPracticeLesson());return}
        val state=cycleState?.takeIf{it.currentLessonId==activeLessonId}
            ?:AutonomousPracticePolicy.start(activeLessonId,focusedWords,carePlan.focusMinutes)
        if(state==null){moveToWord(nextPracticeLesson());return}
        val next=AutonomousPracticePolicy.advance(state,
            cycleSignal?:WordCycleSignal(false,false,childRequestedHelp),wordProgress,
            soundTracker.prioritizedSound()?.token,practiceReferences)
        cycleState=next.state;cycleSignal=null
        moveToWord(next.nextLessonId)
    }
    fun resumeWordPractice(){
        cancelGuidance();automaticRoundAllowed=false
        vm.cancelPraise(praiseTicket);praiseTicket=null;vm.cancelPraise(roundPraiseTicket);roundPraiseTicket=null
        speaker?.stop()
        val roundElapsed=roundForegroundCharge+if(roundStartedAt>0)(android.os.SystemClock.elapsedRealtime()-roundStartedAt).coerceAtLeast(0)else 0
        val resumed=if(autonomous && wordClock.reason==LetterPause.ROUND)
            WordLearningPacing.continueAutonomousRound(wordClock,roundElapsed)
            else WordLearningPacing.resume(wordClock)
        roundStartedAt=0;roundForegroundCharge=0
        if(resumed.roundPractised==0)roundParticipation=0
        wordClock=resumed
        if(!resumed.paused){
            val previous=activeLessonId
            pendingNextId?.let{activeLessonId=it;pendingNextId=null;resetPictureTurn()}
            audioBoundary.foreground();phase=Phase.IDLE
            if(autonomous && previous==activeLessonId){
                if(soundUiState.opened)requestGuide(GuidePurpose.INTRO)else awaitingAttempt=true
            }
        }
    }
    fun pauseCurrentPractice(){
        vm.cancelPraise(praiseTicket);praiseTicket=null;vm.cancelPraise(letterPraiseTicket)
        vm.cancelPraise(roundPraiseTicket);roundPraiseTicket=null
        audioBoundary.background();presentation=null
        if(letterTarget!=null)onLetterBreak?.invoke() else {
            if(autonomous && wordClock.reason==LetterPause.ROUND){
                wordClock=WordLearningPacing.continueAutonomousRound(wordClock,roundForegroundCharge)
                roundStartedAt=0;roundForegroundCharge=0
            }
            tally=tally.record(SessionEvent.Break);wordClock=wordClock.pause(LetterPause.USER);phase=Phase.PAUSED
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            vm.cancelPraise(praiseTicket);vm.cancelPraise(letterPraiseTicket)
            vm.cancelPraise(roundPraiseTicket);vm.cancelPraise(handoffTicket)
            audioBoundary.close()
            speaker?.shutdown()
            engineOwner.close()
            recorder.close()
            soundTracker.clear()
        }
    }

    // DEC-056: a completed inference can never follow the learner to another letter.
    LaunchedEffect(letterTarget?.id) {
        if (letterTarget != null && initialPreview==null) {
            attemptGeneration.invalidate()
            recorder.cancel()
            speaker?.stop()
            presentation = null
            lastDevelopmentResult = null
            errorMsg = null
            phase = Phase.IDLE
            lessonScroll.scrollTo(0)
            settledLetterId=letterTarget.id
        }
    }

    fun beginRecording() {
        if(isPublicPreview)return
        if(!audioBoundary.isForeground)return
        cancelGuidance();awaitingAttempt=false
        vm.cancelPraise(praiseTicket);praiseTicket=null
        vm.cancelPraise(letterPraiseTicket);attemptHasSamples=false
        speaker?.stop()
        if (!LocalWordPractice.canCapture(BuildConfig.DEBUG)) {
            errorMsg = "Recording is unavailable in this version. You can still listen and practise."
            return
        }
        if (engine == null) {
            errorMsg = "Sound practice is getting ready. Please try again in a moment."
            return
        }
        val generation=attemptGeneration.next()
        phase=Phase.PREPARING
        errorMsg=null
        scope.launch {
            val tick=android.os.SystemClock.elapsedRealtime()
            val started=try{recorder.start()}catch(cancel:CancellationException){throw cancel}catch(_:Exception){false}
            android.util.Log.i("VaakMitraMic","startMs=${android.os.SystemClock.elapsedRealtime()-tick} started=$started")
            if(vm.wordIdentity()==learningIdentity && attemptGeneration.isCurrent(generation) && phase==Phase.PREPARING && audioBoundary.isForeground){
                phase=if(started)Phase.RECORDING else Phase.IDLE
                if(!started)errorMsg="Microphone is busy. Try again."
            }
        }
    }

    val micPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val valid=audioBoundary.consumePermission(pendingPermission)
        pendingPermission=null
        if(valid && granted && phase==Phase.IDLE)beginRecording()
        else if(valid && !granted)errorMsg="Microphone permission is needed to practice."
    }

    fun onMicTap() {
        if(isPublicPreview)return
        if(guideRunning)return
        if(letterTarget==null && wordClock.paused)return
        when (phase) {
            Phase.PREPARING -> {attemptGeneration.invalidate();recorder.cancel();phase=Phase.IDLE}
            Phase.IDLE -> {
                presentation = null
                lastDevelopmentResult = null
                if (!LocalWordPractice.canCapture(BuildConfig.DEBUG)) {
                    errorMsg = "Recording is unavailable in this version. You can still listen and practise."
                    return
                }
                val has = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
                if (has) beginRecording() else {
                    pendingPermission=audioBoundary.requestPermission()
                    if(pendingPermission!=null)micPermission.launch(Manifest.permission.RECORD_AUDIO)
                }
            }
            Phase.RECORDING -> {
                phase = Phase.PROCESSING
                val generation = attemptGeneration.next()
                scope.launch {
                    val targetWord = StarterWords.byNumericLessonId(activeLessonId)
                    val capture = try {withContext(Dispatchers.IO) {
                        val tick=android.os.SystemClock.elapsedRealtime()
                        val samples = recorder.stop()
                        android.util.Log.i("VaakMitraMic","stopMs=${android.os.SystemClock.elapsedRealtime()-tick}")
                        val count=samples.size
                        try {
                            val activeEngine = engine
                            val assessed=if (letterTarget != null) {
                                activeEngine?.assessLetter(letterTarget.id, samples)
                                    ?: com.team96.speakeasy.audio.LocalWordOutcome(reason = "MODEL_UNAVAILABLE", developmentResult = "DEV_UNAVAILABLE")
                            } else if (targetWord == null || activeEngine == null) {
                                LocalWordPractice.assess(targetWord?.tamil.orEmpty(), samples)
                            } else {
                                activeEngine.assess(targetWord.id, samples)
                            }
                            assessed to count
                        }
                        finally { samples.fill(0) }
                    }}catch(cancel:CancellationException){throw cancel}catch(_:Exception){
                        if(attemptGeneration.isCurrent(generation)&&phase==Phase.PROCESSING){phase=Phase.IDLE;errorMsg="This recording could not be completed. You can try again when ready."}
                        return@launch
                    }
                    val assessed=capture.first;val sampleCount=capture.second
                    if (vm.wordIdentity()==learningIdentity && attemptGeneration.isCurrent(generation) && phase == Phase.PROCESSING && (letterTarget!=null || !wordClock.paused)) {
                        val wordId = StarterWords.byNumericLessonId(activeLessonId)?.id ?: "LESSON-$activeLessonId"
                        attemptHasSamples=hasRecordedSamples(sampleCount)
                        if(attemptHasSamples){if(letterTarget==null){tally=tally.record(SessionEvent.Attempt(wordId,assessed.reason));turnParticipation=true}else onLetterAttempt?.invoke()}
                        lastDevelopmentResult = assessed.developmentResult
                        voiceCoachCue=assessed.coachCue
                        coachAlignment=assessed.pauseAlignment
                        if(letterTarget==null){soundTracker.record(assessed.soundPracticeEvidence);soundRevision++}
                        if(autonomous)cycleSignal=WordCycleSignal(
                            assessed.reason=="PHONEME_TOKENS" && assessed.soundPracticeEvidence!=null,
                            assessed.soundPracticeEvidence?.sequenceAgrees==true,childRequestedHelp)
                        presentation = if (letterTarget == null) LocalWordPractice.present(assessed).let{shown->
                            if(autonomous)shown.copy(
                                title=if(assessed.predictedPhonemes.isNullOrEmpty())"Let's listen together" else shown.title,
                                guidance=assessed.coachCue?.caption?:"Your guide will choose the next practice step. You can always pause.",
                                primaryActionLabel="Next word",canAdvancePractice=true,
                            )else shown
                        } else {
                            // Unvalidated isolated-letter predictions never judge a learner's attempt.
                            WordPracticePresentation(
                                title = if (assessed.reason == "PHONEME_TOKENS") "Predicted sounds" else "Sound feedback unavailable",
                                guidance = "These sounds are an estimate. You can practise again or mark your practice complete.",
                                tokenSequence = assessed.predictedPhonemes?.joinToString(" "),
                                detailCode = assessed.reason,
                            )
                        }
                        phase = Phase.RESULT
                        if(autonomous)requestGuide(GuidePurpose.FEEDBACK)
                        // DEC063: appreciate the attempt, independent of the decoder's verdict.
                        if(recordedPraiseEligible(sampleCount,letterTarget!=null,letterRewardsEnabled))praise(PraiseEvent.PRACTICE)
                    }
                }
            }
            else -> {}
        }
    }

    LaunchedEffect(activeLessonId,autonomous,lifecycleResumed){
        if(autonomous && lifecycleResumed && !wordClock.paused && !finishing){
            if(cycleState?.currentLessonId!=activeLessonId)
                cycleState=AutonomousPracticePolicy.start(activeLessonId,focusedWords,carePlan.focusMinutes)
            if(phase==Phase.IDLE)requestGuide(GuidePurpose.INTRO)
            else if(phase==Phase.RESULT && cycleSignal!=null)requestGuide(GuidePurpose.FEEDBACK)
        }
    }

    LaunchedEffect(guideRequest){
        val request=guideRequest?:return@LaunchedEffect
        fun allowed()=cueGeneration.isCurrent(request.ticket) && vm.wordIdentity()==learningIdentity &&
            activeLessonId==request.lessonId && !finishing && !wordClock.paused && audioBoundary.isForeground &&
            lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED) &&
            phase==(if(request.purpose==GuidePurpose.INTRO)Phase.IDLE else Phase.RESULT)
        try {
            if(!allowed())return@LaunchedEffect
            // Automatic examples are support too; picture independence must not be overstated.
            extraSupportUsed=true
            vm.cancelPraise(praiseTicket);praiseTicket=null
            val readyUntil=android.os.SystemClock.elapsedRealtime()+1200
            while(allowed() && android.os.SystemClock.elapsedRealtime()<readyUntil &&
                (practiceReferences.isEmpty() || speaker?.readiness==SpeechReadiness.PREPARING))delay(40)
            if(!allowed())return@LaunchedEffect
            val word=StarterWords.byNumericLessonId(request.lessonId)?:return@LaunchedEffect
            val reference=practiceReferences[word.id].orEmpty()
            val focus=soundTracker.prioritizedSound(reference.toSet())
            val cueFocus=if(request.purpose==GuidePurpose.FEEDBACK)PracticeVoiceCoach.focusSound(coachAlignment,reference)else null
            val recipe=focus ?: cueFocus ?: SoundPracticeCatalog.forWord(reference)
            displayedGuideRecipe=recipe
            val state=cycleState?:AutonomousPracticePolicy.start(activeLessonId,focusedWords,carePlan.focusMinutes)
                ?:return@LaunchedEffect
            val signal=cycleSignal
            val steps=when{
                recipe==null -> listOf(2)
                request.manualSpeech || childRequestedHelp -> listOf(0,1,2)
                request.purpose==GuidePurpose.FEEDBACK -> if(PracticeVoiceCoach.needsFullGuide(voiceCoachCue) || signal?.usable==true && !signal.sequenceAgreement)listOf(0,1,2)else listOf(2)
                else -> AutonomousPracticePolicy.guidanceSteps(state,focus!=null||childRequestedHelp,wordProgress)
            }
            val feedbackCue=voiceCoachCue.takeIf{request.purpose==GuidePurpose.FEEDBACK && !request.manualSpeech}
            if(feedbackCue!=null){
                val coached=runCoachPreface(allowed=::allowed,
                    play={
                        val enabled=vm.loadPraiseSettings(context).automaticSpeech
                        enabled && !isPublicPreview && speaker?.speakCoach(feedbackCue)==true
                    },isSpeaking={isSpeaking},stop={if(cueGeneration.isCurrent(request.ticket))speaker?.stop()})
                if(!coached || !allowed())return@LaunchedEffect
            }
            val completed=runGuideCues(steps,GuideCadence(),::allowed,
                onStep={soundUiState=soundUiState.copy(opened=true,step=it)},
                play={step->
                    val enabled=request.manualSpeech || vm.loadPraiseSettings(context).automaticSpeech
                    if(!enabled || isPublicPreview)false
                    else if(recipe!=null)speaker?.speakSoundStep(recipe,step,word.id)==true
                    else speaker?.speakWord(word.tamil)==true
                },isSpeaking={isSpeaking},stop={if(cueGeneration.isCurrent(request.ticket))speaker?.stop()})
            if(completed && allowed()){
                guideRunning=false
                if(request.purpose==GuidePurpose.FEEDBACK)advanceFromWord()
                else awaitingAttempt=true
            }
        } finally {if(cueGeneration.isCurrent(request.ticket))guideRunning=false}
    }

    LaunchedEffect(wordClock.reason,automaticRoundAllowed){
        if(!autonomous || !automaticRoundAllowed || wordClock.reason!=LetterPause.ROUND)return@LaunchedEffect
        val ticket=cueGeneration.next()
        delay(5000) // Existing bounded round cheer settles before the next guided cycle.
        if(cueGeneration.isCurrent(ticket) && automaticRoundAllowed && !finishing &&
            vm.wordIdentity()==learningIdentity && lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED) &&
            phase==Phase.PAUSED && wordClock.reason==LetterPause.ROUND)resumeWordPractice()
    }

    LaunchedEffect(phase) {
        if (phase == Phase.RECORDING) {
            delay(8000)
            onMicTap()
        }
    }

    if (lesson == null) {
        HeritagePage {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("Lesson not found", color = HeritageInk, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(16.dp))
                    BouncyButton("Go Back", listOf(Color(0xFF9A7A63), Color(0xFF705747)), modifier = Modifier.width(200.dp)) { nav.popBackStack() }
                }
            }
        }
        return
    }

    val grad = LessonColors[(lesson.id - 1).coerceAtLeast(0) % LessonColors.size]
    val avatarPhase = when (phase) {
        Phase.IDLE -> AvatarPhase.IDLE
        Phase.PREPARING -> AvatarPhase.PROCESSING
        Phase.RECORDING -> AvatarPhase.LISTENING
        Phase.PROCESSING -> AvatarPhase.PROCESSING
        Phase.RESULT -> if(autonomous)AvatarPhase.IDLE else when (lastDevelopmentResult) {
            "DEV_MATCH" -> AvatarPhase.PRAISE
            "DEV_PHONEMES" -> AvatarPhase.IDLE
            else -> AvatarPhase.RETRY
        }
        Phase.PAUSED -> AvatarPhase.BREAK
    }

    val largeText=LocalDensity.current.fontScale>1.4f
    val soundPractice: @Composable () -> Unit = {
        if(letterTarget==null && (phase==Phase.IDLE || phase==Phase.RESULT) && !wordClock.paused){
            val target=StarterWords.byNumericLessonId(activeLessonId)
            if(target!=null){
                val reference=practiceReferences[target.id].orEmpty()
                val prioritized=remember(soundRevision,activeLessonId,practiceReferences){soundTracker.prioritizedSound(reference.toSet())}
                val cueFocus=if(phase==Phase.RESULT)PracticeVoiceCoach.focusSound(coachAlignment,reference)else null
                val recipe=(if(guideRunning)displayedGuideRecipe else null) ?: prioritized ?: cueFocus ?: SoundPracticeCatalog.forWord(reference)
                SoundPracticeCard(recipe,target.id,prioritized!=null,
                    interactive=audioBoundary.isForeground && !finishing,
                    state=soundUiState,running=guideRunning,awaitingAttempt=awaitingAttempt,
                    spokenGuide=!isPublicPreview && (guideRequest?.manualSpeech==true || vm.loadPraiseSettings(context).automaticSpeech) && speaker?.readiness==SpeechReadiness.READY,
                    cycleLabel=if(autonomous)cycleState?.let{"Cycle ${it.completedCycles+1} · Word ${it.position+1} / ${it.words.size}"}else null,
                    onSkip={
                        cancelGuidance();soundUiState=soundUiState.copy(opened=false)
                        if(autonomous && phase==Phase.RESULT)advanceFromWord()else awaitingAttempt=true
                    },
                    onHelp={
                        requestActivityHelp()
                        if(autonomous)requestGuide(if(phase==Phase.RESULT)GuidePurpose.FEEDBACK else GuidePurpose.INTRO)
                        else if(!isPublicPreview && recipe!=null)speaker?.speakSoundStep(recipe,soundUiState.step,target.id)
                    },onPause={pauseCurrentPractice()},
                )
            }
        }
    }
    val voiceControls: @Composable () -> Unit = {
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(Color(0xFF634330)).padding(vertical=12.dp,horizontal=8.dp),horizontalAlignment=Alignment.CenterHorizontally) {
                Row(horizontalArrangement=Arrangement.spacedBy(16.dp),verticalAlignment=Alignment.CenterVertically) {
                    ActionCircle("Example",Icons.AutoMirrored.Rounded.VolumeUp,Color.White.copy(alpha=.25f)) {
                        if (audioBoundary.isForeground && (phase==Phase.IDLE || phase==Phase.RESULT) && (letterTarget!=null || !wordClock.paused)) {
                            if(letterTarget==null)requestActivityHelp()
                            vm.cancelPraise(praiseTicket);praiseTicket=null;vm.cancelPraise(letterPraiseTicket)
                            if(autonomous){requestGuide(if(phase==Phase.RESULT)GuidePurpose.FEEDBACK else GuidePurpose.INTRO,manualSpeech=true);return@ActionCircle}
                            if(isPublicPreview)return@ActionCircle
                            val spoken = if (letterTarget == null) speaker?.speakWord(lesson.symbol)==true else speaker?.speakLetter(letterTarget.id)==true
                            if (!spoken) errorMsg = "The offline Tamil example is unavailable. You can practise without it."
                        }
                    }
                    MicButton(phase=phase,onTap={onMicTap()},ready=engine!=null && !isPublicPreview && !guideRunning,
                        blockedLabel=if(guideRunning)"Wait for your turn" else "Microphone loading")
                    Spacer(Modifier.size(64.dp))
                }
                Spacer(Modifier.height(9.dp))
                when(phase) {
                    Phase.PREPARING->Text("Getting microphone ready… tap to cancel",color=HeritagePaper,fontWeight=FontWeight.Bold,textAlign=TextAlign.Center)
                    Phase.RECORDING->Text("Listening… tap to stop",color=HeritagePaper,fontWeight=FontWeight.Bold,textAlign=TextAlign.Center)
                    Phase.PROCESSING->Text("Finishing your practice…",color=HeritagePaper,fontWeight=FontWeight.Bold,textAlign=TextAlign.Center)
                    Phase.PAUSED->Text("Taking a break",color=HeritagePaper,fontWeight=FontWeight.Bold)
                    else->Text(if(guideRunning)"Listen and join your guide…" else if(engine==null && !isPublicPreview)"Getting sound practice ready…" else if(autonomous&&awaitingAttempt)"Your turn · use the mic when ready" else if(letterTarget==null)"Example and the mic are optional." else "Tap Example, then use the mic.",color=HeritagePaper,fontSize=12.sp,textAlign=TextAlign.Center)
                }
            }
    }
    HeritagePage {
        Column(Modifier.fillMaxSize().safeDrawingPadding().padding(horizontal=20.dp),horizontalAlignment=Alignment.CenterHorizontally) {
            Column(Modifier.weight(1f).verticalScroll(lessonScroll).padding(top=14.dp,bottom=12.dp),horizontalAlignment=Alignment.CenterHorizontally) {
                HeritageHeading(
                    if (letterTarget == null) "Word practice" else "${letterTarget.group.title} · Level ${TamilAlphabet.all.indexOf(letterTarget)+1}",
                    if (letterTarget == null) "சொற்பயிற்சி" else letterTarget.group.tamil,onBack={finishSession()},compact=letterTarget!=null)
                letterRoundLabel?.let{Text(it,color=HeritageMaroon,fontSize=12.sp,textAlign=TextAlign.Center)}
                Text("Listen, practise and take your time.",color=HeritageMuted,fontSize=12.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(vertical=if(letterTarget==null)10.dp else 4.dp))
                Row(Modifier.fillMaxWidth().padding(vertical=8.dp),verticalAlignment=Alignment.CenterVertically) {
                    Box(Modifier.width(if(letterTarget==null)116.dp else 80.dp).height(if(letterTarget==null)136.dp else 90.dp),contentAlignment=Alignment.BottomCenter) {
                        ExpressiveAvatar(avatarPreference,avatarPhase,speaking=isSpeaking,audioLevel=if(isSpeaking).66f else 0f,modifier=Modifier.fillMaxSize())
                    }
                    Column(Modifier.weight(1f)) {
                        Text(avatarPreference.avatarId.displayName,color=HeritageMaroon,fontSize=14.sp,fontWeight=FontWeight.Bold)
                        Text(
                        when (phase) {
                            Phase.PREPARING -> "Getting ready. Speak when you see Listening."
                            Phase.RECORDING -> "I’m listening. Take your time."
                            Phase.PROCESSING -> "I’m checking this attempt locally."
                            Phase.RESULT -> if (lastDevelopmentResult == "DEV_PHONEMES") {
                                "Here are the sounds I heard."
                            } else if (lastDevelopmentResult == "DEV_MATCH") {
                                "Thank you for practising. Take your next small step when ready."
                            } else {
                                if (letterTarget == null) "Listen once more, then say the whole word again." else "You can practise again or finish when ready."
                            }
                            Phase.PAUSED -> "Take the time you need."
                            else -> if(guideRunning)"Let's say it together." else if(autonomous&&awaitingAttempt)"Your turn. Take your time."
                                else if (letterTarget == null) wordIdlePrompt(StarterWords.byNumericLessonId(activeLessonId)!!.id,contextExplored) else "One letter, at your pace."
                        },
                            color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=18.sp,lineHeight=25.sp,
                        )
                    }
                }
                if (letterTarget != null) LetterTraceSlate(letterTarget.symbol,TamilAlphabet.all.indexOf(letterTarget),compact=true)
                // Keep the next teaching glyph visible when completion feedback wraps at large text sizes.
                if(letterPracticeMark)Text("நன்று · Practice recorded",color=HeritageMaroon,fontSize=13.sp)
                if(phase==Phase.IDLE)soundPractice()
                if(letterTarget!=null && letterPracticeMark && letterPraiseSerial>0 && settledLetterId==letterTarget.id && phase==Phase.IDLE){
                    EncouragementPanel(vm,PraiseEvent.PRACTICE,eventKey=letterPraiseTicket?:"restored-letter",automatic=true,enabled=phase==Phase.IDLE&&!finishing,speak=::speakPraise,stop={speaker?.stopPraise()},voiceStatus={speaker?.readiness?:SpeechReadiness.UNAVAILABLE})
                }
                if(letterTarget==null){
                    val target=StarterWords.byNumericLessonId(activeLessonId)
                    if(target!=null){
                        Spacer(Modifier.height(12.dp))
                        InterestLearningCard(target,pictureProgressWithSupport(wordProgress[target.id]?:PictureProgress(),extraSupportUsed),InterestTheme.entries.firstOrNull{it.name==interestScene}?:InterestTheme.NEUTRAL,turnIndex,wordClock.roundPractised,pictureFeedback,
                            phase==Phase.IDLE && !guideRunning && !learningWritePending && !wordClock.paused && wordReady,partsOpen,
                            onScene={interestScene=it.name},
                            onChoice={selected,options->
                                if(phase==Phase.IDLE && !wordClock.paused && !learningWritePending && pictureFeedback!=true){
                                    val selection=choosePictureWithSupport(target.id,selected,options,wordProgress[target.id]?:PictureProgress(),java.time.LocalDate.now().toEpochDay(),extraSupportUsed)
                                    val response=selection.response
                                    tally=tally.record(SessionEvent.PictureChoice(target.id,response.matched,selection.withoutExtraHint))
                                    sessionPictures=sessionPictures+(target.id to response.progress)
                                    pictureFeedback=response.matched
                                    if(response.matched){turnParticipation=true;if(!markedTurn){
                                        if(!autonomous){markedTurn=true;countWordTurn(true)}
                                        praise(PraiseEvent.PICTURE)
                                    }}
                                    if(response.progress.needsBreak){vm.cancelPraise(praiseTicket);praiseTicket=null;wordClock=wordClock.pause(LetterPause.SUPPORT)}
                                    learningWritePending=true
                                    scope.launch{try{val ok=withContext(Dispatchers.IO){vm.recordWordProgress(learningIdentity,target.id,response.progress)};if(!ok)errorMsg="This turn could not be saved. You can keep practising."}finally{learningWritePending=false}}
                                }
                            },
                            onHelp={requestActivityHelp()},onParts={if(!partsOpen)requestActivityHelp();partsOpen=!partsOpen},
                            onAgain={if(!autonomous&&!markedTurn)countWordTurn(turnParticipation);resetPictureTurn()},onNext={advanceFromWord()},onEnough={finishSession()},
                            contextExplored=contextExplored,onContextAction={
                                if(contextExplored)contextExplored=false
                                else if(phase==Phase.IDLE && !wordClock.paused && wordReady && !learningWritePending){
                                    contextExplored=true;tally=tally.record(SessionEvent.ContextTurn(target.id))
                                    // DEC066: viewing the example is exposure, not a completed practice turn.
                                }
                            },automaticCycles=autonomous,encouragement={if(phase==Phase.IDLE&&!wordClock.paused&&!finishing)praiseCue?.let{cue->EncouragementPanel(vm,PraiseEvent.valueOf(cue),eventKey=praiseTicket?:"restored-word",automatic=true,speak=::speakPraise,stop={speaker?.stopPraise()},voiceStatus={speaker?.readiness?:SpeechReadiness.UNAVAILABLE})}})
                        if(!wordReady)Text("Loading saved picture practice…",color=HeritageMuted,fontSize=12.sp)
                    }
                }
                Text(lesson.english,color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=25.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(top=12.dp))
                if(letterTarget?.group==LetterGroup.UYIRMEI) Text("${TamilAlphabet.find(letterTarget.meiId.orEmpty())?.symbol} + ${TamilAlphabet.find(letterTarget.uyirId.orEmpty())?.symbol} = ${letterTarget.symbol}",color=HeritageMaroon,fontSize=23.sp,textAlign=TextAlign.Center)
                Text(lesson.phoneme,color=HeritageMuted,fontSize=15.sp,textAlign=TextAlign.Center)
                if(letterTarget != null) Text(if(letterTarget.group==LetterGroup.AYTHAM) "Example reads the letter name: Aytham" else "You can listen, look or trace before you speak.",color=HeritageMuted,fontSize=12.sp,textAlign=TextAlign.Center)
                Spacer(Modifier.height(18.dp))
                Box(Modifier.fillMaxWidth().border(1.dp,HeritageGold,RoundedCornerShape(12.dp)).padding(14.dp)) {
                    Text(lesson.tip,color=HeritageMuted,fontSize=15.sp,lineHeight=22.sp,textAlign=TextAlign.Center,modifier=Modifier.fillMaxWidth())
                }
                errorMsg?.let{Text(it,color=HeritageMaroon,fontSize=14.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(top=14.dp))}
                if(largeText){Spacer(Modifier.height(16.dp));voiceControls()}
            }
            if(!largeText) voiceControls()
            Spacer(Modifier.height(10.dp))
            if(letterTarget != null) {
                HeritageButton("Practice complete",onClick={onLetterComplete?.invoke()},enabled=phase==Phase.IDLE,modifier=Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
            }
            HeritageButton("Break / Stop",danger=true,modifier=Modifier.fillMaxWidth(),onClick={
                pauseCurrentPractice()
            })
            Spacer(Modifier.height(12.dp))
        }
        AnimatedVisibility(
            visible = phase == Phase.RESULT && presentation != null,
            enter = fadeIn(tween(300)) + scaleIn(tween(400))
        ) {
            // Compose can retain exit content after state becomes null; never force-unwrap it.
            presentation?.let { currentPresentation ->
                PracticeResultOverlay(
                    currentPresentation,
                    soundPractice=soundPractice,
                    encouragement={if(attemptHasSamples&&(letterTarget==null||letterRewardsEnabled))EncouragementPanel(vm,PraiseEvent.PRACTICE,heading="Practice encouragement",eventKey=praiseTicket?:"preview-attempt",automatic=true,enabled=phase==Phase.RESULT&&!finishing,speak=::speakPraise,stop={speaker?.stopPraise()},voiceStatus={speaker?.readiness?:SpeechReadiness.UNAVAILABLE})},
                    onRetry = if(!autonomous && letterTarget==null && currentPresentation.canAdvancePractice && currentPresentation.tokenSequence!=null) ({cancelGuidance();attemptGeneration.invalidate();presentation=null;lastDevelopmentResult=null;phase=Phase.IDLE}) else null,
                    onLetterComplete = if(letterTarget != null) ({
                        attemptGeneration.invalidate();presentation=null;phase=Phase.IDLE;onLetterComplete?.invoke();Unit
                    }) else null,
                    onPrimary = {
                        attemptGeneration.invalidate()
                        presentation = null
                        lastDevelopmentResult = null
                        if (lesson.type == "letter") { phase = Phase.IDLE; return@PracticeResultOverlay }
                        if (currentPresentation.canAdvancePractice) {
                            advanceFromWord()
                        } else {
                            phase = Phase.IDLE
                        }
                    },
                    onClose = { finishSession() },
                )
            }
        }
        AnimatedVisibility(visible = phase == Phase.PAUSED, enter = fadeIn(tween(200))) {
            HeritagePage {
                Column(Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp),horizontalAlignment=Alignment.CenterHorizontally) {
                    Spacer(Modifier.height(28.dp));KolamMark(Modifier.size(90.dp))
                    ExpressiveAvatar(avatarPreference,AvatarPhase.BREAK,modifier=Modifier.width(120.dp).height(142.dp))
                    Spacer(Modifier.height(12.dp))
                    Text(if(wordClock.ended)"A good time to finish." else if(autonomous&&automaticRoundAllowed)"Cycle complete" else "Break time",color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=32.sp)
                    Text(if(wordClock.ended)"Your planned session time is complete." else if(autonomous&&automaticRoundAllowed)"Your guide will continue the next cycle. You can take a break instead." else "Take your time. Your guide is here.",color=HeritageMuted,fontSize=17.sp,textAlign=TextAlign.Center,modifier=Modifier.padding(vertical=20.dp))
                    if(autonomous&&automaticRoundAllowed){
                        HeritageButton("Take a break",onClick={pauseCurrentPractice()},danger=true,modifier=Modifier.fillMaxWidth())
                        Spacer(Modifier.height(12.dp))
                    }
                    if(earnedPraiseRound(wordClock.reason,roundParticipation,wordClock.roundSize))EncouragementPanel(vm,PraiseEvent.ROUND,heading="Your round stamp",eventKey=roundPraiseTicket?:"restored-round",automatic=true,enabled=!finishing,speak=::speakPraise,stop={speaker?.stopPraise()},voiceStatus={speaker?.readiness?:SpeechReadiness.UNAVAILABLE})
                    if(!wordClock.ended&&!terminalRound)HeritageButton("Continue",onClick={resumeWordPractice()},modifier=Modifier.fillMaxWidth())
                    Spacer(Modifier.height(14.dp))
                    HeritageButton("End session",onClick={finishSession()},secondary=true,modifier=Modifier.fillMaxWidth())
                }
            }
        }
    }
}

@Composable
private fun MicButton(phase: Phase, onTap: () -> Unit,ready:Boolean=true,blockedLabel:String="Microphone loading") {
    val recording = phase == Phase.RECORDING
    val t = rememberInfiniteTransition(label = "mic")
    val pulse by t.animateFloat(1f, 1.18f, infiniteRepeatable(tween(700), RepeatMode.Reverse), label = "pulse")
    val scale = if (recording) pulse else 1f
    Box(contentAlignment = Alignment.Center) {
        if (recording) {
            Box(Modifier.size(110.dp).scale(pulse).clip(CircleShape).background(Color.White.copy(alpha = 0.25f)))
        }
        Box(
            Modifier
                .size(92.dp)
                .scale(scale)
                .shadow(14.dp, CircleShape)
                .clip(CircleShape)
                .background(Brush.linearGradient(if (recording) listOf(Color(0xFF9B243D), Color(0xFFD62828)) else listOf(Color.White, Color(0xFFF1E3D5))))
                .clickable(enabled = (ready && phase == Phase.IDLE) || phase==Phase.PREPARING || recording) { onTap() },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                if (recording) Icons.Rounded.Stop else Icons.Rounded.Mic,
                contentDescription = if (recording) "Stop recording" else if(phase==Phase.PREPARING)"Cancel microphone startup" else if(!ready)blockedLabel else "Start recording",
                tint = if (recording) Color.White else Purple,
                modifier = Modifier.size(44.dp)
            )
        }
    }
}

@Composable
private fun ActionCircle(label: String, icon: androidx.compose.ui.graphics.vector.ImageVector, bg: Color, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            Modifier.size(64.dp).clip(CircleShape).background(bg).clickable { onClick() },
            contentAlignment = Alignment.Center
        ) { Icon(icon, label, tint = Color.White, modifier = Modifier.size(32.dp)) }
        Spacer(Modifier.height(6.dp))
        Text(label, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun PracticeResultOverlay(presentation:WordPracticePresentation,onPrimary:()->Unit,onClose:()->Unit,onLetterComplete:(()->Unit)?=null,onRetry:(()->Unit)?=null,encouragement:@Composable ()->Unit={},soundPractice:@Composable ()->Unit={}) {
    Box(Modifier.fillMaxSize().background(Color(0xD1292438)),contentAlignment=Alignment.Center) {
        Column(Modifier.fillMaxWidth().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(22.dp).clip(RoundedCornerShape(19.dp)).background(HeritagePaper).border(1.dp,HeritageGold,RoundedCornerShape(19.dp)).padding(22.dp),horizontalAlignment=Alignment.CenterHorizontally) {
            KolamMark(Modifier.size(58.dp))
            Text(presentation.title,color=HeritageInk,fontFamily=FontFamily.Serif,fontSize=28.sp,fontWeight=FontWeight.Bold,textAlign=TextAlign.Center)
            presentation.tokenSequence?.let{sequence->
                Spacer(Modifier.height(15.dp))
                Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(HeritageSlate).padding(18.dp)) {
                    Text(sequence,color=HeritagePaper,fontSize=24.sp,textAlign=TextAlign.Center,modifier=Modifier.fillMaxWidth())
                }
            }
            Spacer(Modifier.height(16.dp))
            Text(presentation.guidance,color=HeritageMuted,fontSize=17.sp,lineHeight=24.sp,textAlign=TextAlign.Center)
            soundPractice()
            encouragement()
            Spacer(Modifier.height(24.dp))
            if(onLetterComplete != null) {
                HeritageButton("Practice complete",onLetterComplete,modifier=Modifier.fillMaxWidth())
                Spacer(Modifier.height(12.dp))
            }
            HeritageButton(presentation.primaryActionLabel,onPrimary,modifier=Modifier.fillMaxWidth())
            Spacer(Modifier.height(12.dp))
            if(onRetry!=null){HeritageButton("Practise again",onRetry,secondary=true,modifier=Modifier.fillMaxWidth());Spacer(Modifier.height(12.dp))}
            HeritageButton("End session",onClose,secondary=true,modifier=Modifier.fillMaxWidth())
        }
    }
}

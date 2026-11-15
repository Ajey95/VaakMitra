package com.team96.speakeasy
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.team96.speakeasy.journey.*
import com.team96.speakeasy.ui.components.BrandWelcome
import com.team96.speakeasy.ui.navigation.Routes
import com.team96.speakeasy.ui.screens.*
import com.team96.speakeasy.ui.theme.SpeakEasyTheme
import com.team96.speakeasy.viewmodel.*
/** DEC057: nonexported debug-only gallery, public identity/history, no real profile mutations. */
open class ThemeGalleryTestActivity:ComponentActivity(){
 var previewReportWrites=0;private set
 var candleProbeStops=0;private set
 override fun onCreate(savedInstanceState:Bundle?){
  super.onCreate(savedInstanceState)
  window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON)
  enableEdgeToEdge(statusBarStyle=androidx.activity.SystemBarStyle.light(android.graphics.Color.TRANSPARENT,android.graphics.Color.TRANSPARENT),navigationBarStyle=androidx.activity.SystemBarStyle.light(android.graphics.Color.TRANSPARENT,android.graphics.Color.TRANSPARENT))
  val page=intent.getStringExtra("page")?:"splash"
  setContent{SpeakEasyTheme{Surface(Modifier.fillMaxSize()){
   val nav=rememberNavController();val app=remember{AppViewModel(preview=true,reportWriter={previewReportWrites++},previewStars=when(page){"rewards-unknown"->null;"rewards-earned"->35;else->0},previewInterest=when(page){"interest-trains"->"trains";"interest-animals"->"animals";else->"stories"})};val auth=remember{AuthViewModel(preview=true)}
   val routes=mapOf("splash" to "brand-preview","onboarding" to Routes.ONBOARDING,"login" to Routes.LOGIN,"register" to Routes.REGISTER,"home" to Routes.HOME,"lessons" to Routes.LESSONS,"words" to "words-preview","letters" to "letters-preview","letter" to "letter-preview","word" to "word-preview","interest-trains" to "word-preview","interest-animals" to "word-preview","interest-stories" to "word-preview","context-vendum" to "word-preview","picture-hand" to "word-preview","letter-result-off" to "letter-result-preview","letter-result-on" to "letter-result-preview","word-result" to "word-result-preview","word-result-end" to "word-result-preview","word-terminal-round" to "word-terminal-round-preview","avatars" to Routes.AVATAR_PICKER,"caregiver" to Routes.CARE_SETUP,"profile" to Routes.PROFILE,"progress" to Routes.PROGRESS,"rewards" to Routes.REWARDS,"summary" to Routes.SUMMARY,"checkup" to Routes.CHECKUP,"candle" to Routes.CANDLE)
   NavHost(navController=nav,startDestination=if(page.startsWith("auto-"))"autonomous-preview" else if(page in listOf("candle-active","candle-win","candle-ended"))page else if(page.startsWith("rewards-"))Routes.REWARDS else routes[page]?:"brand-preview"){
    // DEC070: explicit public automatic-loop fixtures. No real mic, voice, profile writes or trained-child claims.
    composable("autonomous-preview"){
     val feedback=page in listOf("auto-feedback","auto-round")
     PracticeScreen(nav,app,1,publicPreviewAutonomous=true,
      publicPreviewCompletedTurns=if(page=="auto-round")2 else 0,
      publicPreviewOutcome=if(feedback)com.team96.speakeasy.audio.LocalWordOutcome(
       reason="PHONEME_TOKENS",developmentResult="DEV_PHONEMES",predictedPhonemes=listOf("a","m","m","aː"),
       soundPracticeEvidence=com.team96.speakeasy.audio.SoundPracticeEvidence("TA_WORD_0001",emptySet(),sequenceAgrees=true))else null)
    }
    for(probe in listOf("candle-active","candle-win","candle-ended"))composable(probe){
     val fake=remember{object:com.team96.speakeasy.audio.CandleInput{
      override var isRunning=false;private set
      private var starts=0
      override fun start():Boolean{starts++;isRunning=probe!="candle-ended"||starts>1;return true}
      override fun amplitude()=if(probe=="candle-win")32767 else 0
      override fun cancel(){if(isRunning){isRunning=false;candleProbeStops++}}
     }}
     CandleGameScreen(nav,input=fake)
    }
    composable("brand-preview"){BrandWelcome()}
    composable(Routes.ONBOARDING){OnboardingScreen(nav)}
    composable(Routes.LOGIN){LoginScreen(nav,auth)}
    composable(Routes.REGISTER){RegisterScreen(nav,auth)}
    composable(Routes.HOME){HomeScreen(nav,app)}
    composable(Routes.LESSONS){LessonsScreen(nav,app)}
    composable("words-preview"){LessonsScreen(nav,app,initialSection="WORDS")}
    composable("letters-preview"){TamilLetterBrowser(LetterGroup.UYIR,onBack={nav.popBackStack()},onLetter={nav.navigate("letter-preview")})}
    composable("letter-preview"){LetterLearningScreen("TA_LETTER_UYIR_01",onBack={nav.popBackStack()},nav=nav,vm=app)}
    composable("${Routes.LETTER}/{letterId}",arguments=listOf(navArgument("letterId"){type=NavType.StringType})){entry->LetterLearningScreen(entry.arguments?.getString("letterId").orEmpty(),onBack={nav.popBackStack()},nav=nav,vm=app)}
    composable("word-preview"){PracticeScreen(nav,app,when(page){"context-vendum"->4;"picture-hand"->24;else->1})}
    composable("letter-result-preview"){PracticeScreen(nav,app,0,letterTarget=com.team96.speakeasy.journey.TamilAlphabet.find("TA_LETTER_UYIR_01"),letterRewardsEnabled=page!="letter-result-off",publicPreviewOutcome=com.team96.speakeasy.audio.LocalWordOutcome(reason="PHONEME_TOKENS",developmentResult="DEV_PHONEMES",predictedPhonemes=listOf("a")))}
    composable("word-result-preview"){PracticeScreen(nav,app,if(page=="word-result-end")25 else 2,focusedWords=true,publicPreviewOutcome=com.team96.speakeasy.audio.LocalWordOutcome(reason="PHONEME_TOKENS",developmentResult="DEV_PHONEMES",predictedPhonemes=listOf("a")))}
    composable("word-terminal-round-preview"){PracticeScreen(nav,app,25,focusedWords=true,publicPreviewOutcome=com.team96.speakeasy.audio.LocalWordOutcome(reason="PHONEME_TOKENS",developmentResult="DEV_PHONEMES",predictedPhonemes=listOf("a")),publicPreviewCompletedTurns=2)}
    composable("${Routes.PRACTICE}/{lessonId}?focused={focused}",arguments=listOf(navArgument("lessonId"){type=NavType.IntType},navArgument("focused"){type=NavType.BoolType;defaultValue=false})){entry->PracticeScreen(nav,app,entry.arguments?.getInt("lessonId")?:1,focusedWords=entry.arguments?.getBoolean("focused")?:false)}
    composable(Routes.AVATAR_PICKER){AvatarPickerScreen(nav,preview=true)}
    composable(Routes.CARE_SETUP){CaregiverSetupScreen(nav,preview=true)}
    composable(Routes.PROFILE){ProfileScreen(nav,auth,ProfileDisplay("Caregiver","Sample learner","caregiver@example.test"))}
    composable(Routes.PROGRESS){ProgressScreen(nav,report=null)}
    composable(Routes.REWARDS){RewardsScreen(nav,app)}
    composable(Routes.SUMMARY){val current=app.currentSessionSummary;SessionSummaryScreen(nav,report=current?.report,saveStatus=current?.status,vm=app)}
    composable(Routes.CHECKUP){CheckupScreen(nav)}
    composable(Routes.CANDLE){CandleGameScreen(nav,preview=true)}
   }
  }}}
 }
}
class ThemeGalleryLargeFontTestActivity:ThemeGalleryTestActivity(){override fun attachBaseContext(base:android.content.Context){val c=android.content.res.Configuration(base.resources.configuration);c.fontScale=2f;super.attachBaseContext(base.createConfigurationContext(c))}}

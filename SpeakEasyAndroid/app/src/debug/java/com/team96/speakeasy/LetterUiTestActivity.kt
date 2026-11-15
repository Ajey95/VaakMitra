package com.team96.speakeasy

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.team96.speakeasy.journey.*
import com.team96.speakeasy.ui.screens.*
import com.team96.speakeasy.ui.theme.SpeakEasyTheme
import com.team96.speakeasy.viewmodel.AppViewModel

/** DEC-053: internal debug-only rendered-state host; no production/exported entry point. */
open class LetterUiTestActivity:ComponentActivity() {
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON)
        enableEdgeToEdge(statusBarStyle=androidx.activity.SystemBarStyle.light(android.graphics.Color.TRANSPARENT,android.graphics.Color.TRANSPARENT),navigationBarStyle=androidx.activity.SystemBarStyle.light(android.graphics.Color.TRANSPARENT,android.graphics.Color.TRANSPARENT))
        val initial=intent.getIntExtra("completed",0)
        val startLetter=intent.getStringExtra("letter")
        val screen=intent.getStringExtra("screen").orEmpty()
        setContent{SpeakEasyTheme{Surface(Modifier.fillMaxSize()){
            var count by rememberSaveable{mutableIntStateOf(initial)}
            var selected by rememberSaveable{mutableStateOf(startLetter)}
            val progress=LetterProgress.restore(count)
            val nav=androidx.navigation.compose.rememberNavController()
            val vm=remember{AppViewModel(preview=true)}
            if(screen=="word"){
                PracticeScreen(nav,vm,1)
            }else if(selected!=null){
                LetterLearningScreen(selected!!,nav=nav,vm=vm,onBack={finish()},journey=LetterJourneySnapshot(progress),onPracticeComplete={id->val next=progress.complete(id);val changed=next!=progress;count=next.completedCount;changed})
            }else{
                val group=LetterGroup.entries.firstOrNull{it.name==intent.getStringExtra("group")}?:LetterGroup.UYIR
                TamilLetterBrowser(group,onBack={finish()},onLetter={selected=it},progress=progress)
            }
        }}}
    }
}

/** Activity-scoped font override avoids changing the learner's device settings. */
class LetterLargeFontUiTestActivity:LetterUiTestActivity(){
    override fun attachBaseContext(base:android.content.Context){
        val configuration=android.content.res.Configuration(base.resources.configuration)
        configuration.fontScale=2f
        super.attachBaseContext(base.createConfigurationContext(configuration))
    }
}

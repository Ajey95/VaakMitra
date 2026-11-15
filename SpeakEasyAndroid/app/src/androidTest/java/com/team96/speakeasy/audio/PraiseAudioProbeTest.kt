package com.team96.speakeasy.audio

import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.team96.speakeasy.journey.PraiseEvent
import com.team96.speakeasy.journey.PraiseStyle
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** PRS006: explicit real speaker probe; public sample only, no microphone or settings writes. */
@RunWith(AndroidJUnit4::class)
class PraiseAudioProbeTest {
 @Test fun publicNameOfflineTamilPlaybackAvailabilityIsReported(){
  val instrumentation=InstrumentationRegistry.getInstrumentation();val done=CountDownLatch(1)
  var began=false;var accepted=false;var unavailable=false;var speaker:LocalTamilSpeaker?=null
  instrumentation.runOnMainSync{speaker=LocalTamilSpeaker(instrumentation.targetContext,onUnavailable={unavailable=true;done.countDown()}){speaking->if(speaking)began=true else if(began)done.countDown()}}
  val deadline=SystemClock.elapsedRealtime()+8000
  try{
   do{instrumentation.runOnMainSync{if(!accepted)accepted=speaker?.speakPraise("கவின்",PraiseStyle.HERO,PraiseEvent.ROUND)==true};if(!accepted)SystemClock.sleep(200)}while(!accepted&&SystemClock.elapsedRealtime()<deadline)
   val completed=accepted&&done.await(15,TimeUnit.SECONDS)&&!unavailable
   println("PRS006_REAL_TAMIL_AUDIO accepted=$accepted began=$began completed=$completed unavailable=$unavailable; public_sample_only=true")
   java.io.File(instrumentation.targetContext.cacheDir,"praise-audio-probe.txt").writeText("accepted=$accepted began=$began completed=$completed unavailable=$unavailable\n")
  }finally{instrumentation.runOnMainSync{speaker?.shutdown()}}
 }
}

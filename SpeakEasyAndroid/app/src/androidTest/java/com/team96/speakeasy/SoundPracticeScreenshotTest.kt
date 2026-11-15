package com.team96.speakeasy

import android.content.Intent
import android.graphics.Bitmap
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import java.io.File

/** DEC069: public fixture visual evidence only; gallery stays nonexported, microphone never starts. */
class SoundPracticeScreenshotTest {
    private val instrument get()=InstrumentationRegistry.getInstrumentation()
    private fun find(label:String,visible:Boolean=true):AccessibilityNodeInfo? {
        val ui=instrument.uiAutomation
        if(android.os.Build.VERSION.SDK_INT>=33)ui.clearCache()
        val queue=java.util.ArrayDeque<AccessibilityNodeInfo>();ui.rootInActiveWindow?.let{queue.add(it)}
        while(queue.isNotEmpty()){
            val node=queue.removeFirst()
            if(node.text?.toString()==label && (!visible || node.isVisibleToUser))return node
            repeat(node.childCount){node.getChild(it)?.let{queue.add(it)}}
        };return null
    }
    private fun reveal(label:String):AccessibilityNodeInfo {
        repeat(160){attempt->
            find(label)?.let{return it}
            val queue=java.util.ArrayDeque<AccessibilityNodeInfo>();instrument.uiAutomation.rootInActiveWindow?.let{queue.add(it)}
            while(queue.isNotEmpty()){
                val node=queue.removeFirst()
                if(node.isScrollable && node.isVisibleToUser){node.performAction(if(attempt%16<8)AccessibilityNodeInfo.ACTION_SCROLL_FORWARD else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD);break}
                repeat(node.childCount){node.getChild(it)?.let{queue.add(it)}}
            }
            SystemClock.sleep(150)
        };error("Screenshot control not visible: $label")
    }
    @Test fun coreSoundLayoutAtNormalAndLargeText(){
        for(large in listOf(false,true)){
            val type=if(large)ThemeGalleryLargeFontTestActivity::class.java else ThemeGalleryTestActivity::class.java
            ActivityScenario.launch<ThemeGalleryTestActivity>(Intent(instrument.targetContext,type).putExtra("page","auto-intro")).use{
                reveal("உங்கள் முறை · Your turn")
                val frame=checkNotNull(instrument.uiAutomation.takeScreenshot())
                try{File(instrument.targetContext.filesDir,if(large)"core-sound-large.png" else "core-sound-normal.png").outputStream().use{out->check(frame.compress(Bitmap.CompressFormat.PNG,100,out))}}
                finally{frame.recycle()}
            }
        }
    }
}


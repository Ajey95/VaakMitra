package com.team96.speakeasy

import android.content.Intent
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** DEC069/PHN010: rendered real word-practice surface, public profile, no microphone/TTS/saves. */
@RunWith(AndroidJUnit4::class)
class SoundPracticeInstrumentedTest {
    private val instrumentation get()=InstrumentationRegistry.getInstrumentation()
    private val automation get()=instrumentation.uiAutomation
    private fun find(label:String,visibleOnly:Boolean=true):AccessibilityNodeInfo? {
        if(android.os.Build.VERSION.SDK_INT>=33)automation.clearCache()
        val nodes=java.util.ArrayDeque<AccessibilityNodeInfo>();automation.rootInActiveWindow?.let{nodes.add(it)}
        while(nodes.isNotEmpty()){
            val node=nodes.removeFirst()
            if((!visibleOnly || node.isVisibleToUser) && (node.text?.toString()==label || node.contentDescription?.toString()==label))return node
            repeat(node.childCount){node.getChild(it)?.let{child->nodes.add(child)}}
        }
        return null
    }
    private fun scroll(forward:Boolean):Boolean {
        val nodes=java.util.ArrayDeque<AccessibilityNodeInfo>();automation.rootInActiveWindow?.let{nodes.add(it)}
        while(nodes.isNotEmpty()){
            val node=nodes.removeFirst()
            if(node.isScrollable && node.isVisibleToUser && node.performAction(if(forward)AccessibilityNodeInfo.ACTION_SCROLL_FORWARD else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD))return true
            repeat(node.childCount){node.getChild(it)?.let{child->nodes.add(child)}}
        };return false
    }
    private fun waitFor(label:String):AccessibilityNodeInfo {
        var forward=true
        repeat(140){
            find(label)?.let{return it}
            find(label,visibleOnly=false)?.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.id)
            if(it>3 && !scroll(forward))forward=!forward
            SystemClock.sleep(100)
        }
        fail("Visible control missing: $label");throw IllegalStateException(label)
    }
    private fun click(label:String){var node:AccessibilityNodeInfo?=waitFor(label);while(node!=null){if(node.performAction(AccessibilityNodeInfo.ACTION_CLICK)){SystemClock.sleep(180);return};node=node.parent};fail("Not clickable: $label")}
    private fun launch(page:String,large:Boolean=false)=ActivityScenario.launch<ThemeGalleryTestActivity>(
        Intent(instrumentation.targetContext,if(large)ThemeGalleryLargeFontTestActivity::class.java else ThemeGalleryTestActivity::class.java).putExtra("page",page))

    @Test fun phn011GuideRunsSoundSyllableAndWordWithoutStepSelections(){
        launch("auto-intro").use{scene->
            waitFor("1 / 3 · Sound");assertNull(find("Next part"))
            waitFor("2 / 3 · Syllable");waitFor("உங்கள் முறை · Your turn")
            assertNull(find("Stop recording"))
            assertNull(find("Tamil reward companion in a veshti and cooling glasses"))
            scene.onActivity{assertEquals(0,it.previewReportWrites)}
        }
    }
    @Test fun phn011FeedbackAutomaticallyChoosesTheNextWord(){
        launch("auto-feedback").use{scene->
            waitFor("Cycle 1 · Word 2 / 3");waitFor("உங்கள் முறை · Your turn")
            assertNull(find("Predicted sounds"));assertNull(find("Stop recording"))
            scene.onActivity{assertEquals(0,it.previewReportWrites)}
        }
    }
    @Test fun phn011PauseStopsAutomaticCuesUntilExplicitContinue(){
        launch("auto-intro").use{
            waitFor("1 / 3 · Sound");click("Pause");waitFor("Break time")
            SystemClock.sleep(3200)
            assertNotNull(find("Break time"));assertNull(find("Cycle 1 · Word 2 / 3"))
        }
    }
    @Test fun phn011SkippedCueDoesNotReappearOrStartTheMic(){
        launch("auto-intro").use{
            waitFor("1 / 3 · Sound");click("Skip this cue");waitFor("உங்கள் முறை · Your turn")
            SystemClock.sleep(3200)
            assertNull(find("1 / 3 · Sound"));assertNull(find("Stop recording"))
        }
    }
    @Test fun phn011RoundCelebrationContinuesAutomaticallyToTheNextCycleWord(){
        launch("auto-round").use{
            waitFor("Your round stamp")
            waitFor("Cycle 1 · Word 2 / 3");waitFor("உங்கள் முறை · Your turn")
            assertNull(find("Break time"))
        }
    }
    @Test fun phn011LargeTextAutomaticFlowKeepsPauseReachable(){
        launch("auto-intro",large=true).use{
            waitFor("உங்கள் முறை · Your turn");click("Pause");waitFor("Break time")
        }
    }
    @Test fun phn011ManualNextCancelsThePendingAutomaticNext(){
        launch("auto-feedback").use{
            click("Next word");waitFor("Cycle 1 · Word 2 / 3")
            SystemClock.sleep(4000)
            assertNotNull(find("Cycle 1 · Word 2 / 3"));assertNull(find("Cycle 1 · Word 3 / 3"))
        }
    }
    @Test fun phn011BackgroundNeverRestartsAnOldCue(){
        launch("auto-intro").use{scene->
            waitFor("1 / 3 · Sound")
            scene.moveToState(androidx.lifecycle.Lifecycle.State.STARTED);SystemClock.sleep(3200)
            scene.moveToState(androidx.lifecycle.Lifecycle.State.RESUMED);waitFor("Break time")
            assertNull(find("Cycle 1 · Word 2 / 3"))
        }
    }
    @Test fun phn011CompleteHostWordSetRepeatsAsANewCycleWithoutRewardingSkippedWords(){
        launch("auto-feedback").use{scene->
            // Skip the word without an attempt; a short cue may already have finished.
            waitFor("Cycle 1 · Word 2 / 3");waitFor("உங்கள் முறை · Your turn");click("Next activity")
            waitFor("Cycle 1 · Word 3 / 3");waitFor("உங்கள் முறை · Your turn");click("Next activity")
            waitFor("Cycle 2 · Word 1 / 3")
            assertNull(find("Your round stamp"))
            scene.onActivity{assertEquals(0,it.previewReportWrites)}
        }
    }
    @Test fun phn011TakingARealBreakAtTheCycleBoundaryCancelsAutomaticContinuation(){
        launch("auto-round").use{
            waitFor("Cycle complete");click("Take a break");waitFor("Break time")
            SystemClock.sleep(5400)
            assertNotNull(find("Break time"));assertNull(find("Cycle 1 · Word 2 / 3"))
        }
    }
}

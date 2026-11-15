package com.team96.speakeasy

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.team96.speakeasy.data.SessionManager
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** DEC079/UX014: authentic local entry and sessions; never run resets on a physical phone. */
@RunWith(AndroidJUnit4::class)
class LearnerFlowInstrumentedTest {
    private val instrumentation=InstrumentationRegistry.getInstrumentation()
    private val automation get()=instrumentation.uiAutomation
    private val forbidden=Regex("\\bUNSCORABLE\\b|DEV_|backend|port\\s*8000|\\bAPK\\b|PC server|adult.data|engineering|development check",RegexOption.IGNORE_CASE)

    @Test fun dec079FreshAndReturningLearnerCompleteTheOfflineJourney() {
        assumeTrue(Build.FINGERPRINT.contains("generic") || Build.MODEL.contains("Emulator") || Build.PRODUCT.startsWith("sdk"))
        val alias="Review ${SystemClock.uptimeMillis()}"
        runBlocking { SessionManager.clear() }
        ActivityScenario.launch<MainActivity>(Intent(instrumentation.targetContext,MainActivity::class.java)).use { scene ->
            waitFor("Next");click("Next");click("Next");click("Continue")
            waitFor("Start learning");clean();snapshot("01-welcome")
            click("Start learning");waitFor("Build a comfortable plan");clean()
            val editable=nodes().firstOrNull { it.isEditable }
            assertNotNull("Nickname field",editable)
            editable!!.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,Bundle().apply {
                putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,alias)
            })
            scene.onActivity { activity ->
                val input=activity.getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager
                input.hideSoftInputFromWindow(activity.window.decorView.windowToken,0)
            }
            click("Save plan & choose guide");click("Use this guide")
            waitFor("Word practice",partial=true);clean();snapshot("02-home")
            assertTrue(SessionManager.isOfflineReview);assertTrue(SessionManager.carePlanConfigured)
            assertEquals(alias,SessionManager.carePlan.childAlias)
            scene.onActivity { it.recreate() };waitFor("Word practice",partial=true);clean()
            click("Word practice",partial=true);click("Amma",partial=true)
            waitFor("Break / Stop");clean();snapshot("03-word-practice")
            // No automatic real microphone use. Picture exploration and voluntary session exit are real UI paths.
            waitFor("உங்கள் முறை · Your turn",timeoutMs=60000)
            waitFor("Start recording",timeoutMs=120000)
            click("Picture: Amma",partial=true);waitFor("Picture matched");clean()
            click("Break / Stop");waitFor("End session");snapshot("04-break")
            click("End session");waitFor("Back home");clean();snapshot("05-summary")
            click("Back home");waitFor("Word practice",partial=true)
            click("Progress");waitFor("Practice progress");clean();snapshot("06-progress")
            back();waitFor("Word practice",partial=true)
            click("Continue learning",partial=true);waitFor("Practice complete");clean();snapshot("07-letter-practice")
            click("Practice complete");SystemClock.sleep(500)
            waitFor("Uyir · Level 2",partial=true)
            click("Break / Stop");waitFor("End session");click("End session")
            waitFor("Back to your journey");clean();click("Back to your journey")
            waitFor("Continue learning · ஆ",partial=true)
            click("Profile");waitFor("Caregiver plan");clean();snapshot("08-profile")
            click("Caregiver plan");waitFor("Build a comfortable plan")
            click("Save plan & choose guide");click("Use this guide")
            // Settings must return to its caller, rather than replaying the initial entry reset.
            waitFor("Caregiver plan");clean();snapshot("09-settings-return")
            back();waitFor("Word practice",partial=true)
            scene.onActivity { it.recreate() };waitFor("Word practice",partial=true);clean()
            assertNull(find("Start learning"))
        }
    }

    private fun nodes():List<AccessibilityNodeInfo> {
        if(Build.VERSION.SDK_INT>=33)automation.clearCache()
        val result=mutableListOf<AccessibilityNodeInfo>();val queue=java.util.ArrayDeque<AccessibilityNodeInfo>()
        automation.rootInActiveWindow?.let(queue::add)
        while(queue.isNotEmpty()) { val node=queue.removeFirst();result.add(node);repeat(node.childCount){node.getChild(it)?.let(queue::add)} }
        return result
    }
    private fun find(text:String,partial:Boolean=false)=nodes().firstOrNull { node ->
        node.isVisibleToUser && listOf(node.text?.toString(),node.contentDescription?.toString()).filterNotNull().any { if(partial)it.contains(text) else it==text }
    }
    private fun waitFor(text:String,partial:Boolean=false,timeoutMs:Int=20000):AccessibilityNodeInfo {
        repeat(timeoutMs/200) { attempt ->
            find(text,partial)?.let { return it }
            if(attempt%15==5)reveal(text,partial)?.let{return it}
            SystemClock.sleep(200)
        }
        fail("Missing '$text': "+nodes().mapNotNull { it.text?.toString() }.joinToString(" | "));throw AssertionError()
    }
    private fun reveal(text:String,partial:Boolean):AccessibilityNodeInfo? {
        find(text,partial)?.let{return it}
        repeat(12) {
            val scroller=nodes().firstOrNull{it.isScrollable&&it.isVisibleToUser}
            scroller?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)
            SystemClock.sleep(80)
        }
        repeat(16) {
            find(text,partial)?.let{return it}
            val scroller=nodes().firstOrNull{it.isScrollable&&it.isVisibleToUser}
            scroller?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
            SystemClock.sleep(100)
        }
        return find(text,partial)
    }
    private fun click(text:String,partial:Boolean=false) {
        reveal(text,partial)
        repeat(14) {
            var node=find(text,partial)
            if(node!=null) {
                while(node!=null) {
                    if(node.isClickable && node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) { SystemClock.sleep(350);return }
                    node=node.parent
                }
            }
            val scroller=nodes().firstOrNull { it.isScrollable && it.isVisibleToUser }
            scroller?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD);SystemClock.sleep(200)
        }
        fail("Cannot click '$text': "+nodes().mapNotNull { it.text?.toString() }.joinToString(" | "))
    }
    private fun clean() {
        val copy=nodes().filter { it.isVisibleToUser }.flatMap { listOfNotNull(it.text?.toString(),it.contentDescription?.toString()) }.joinToString("\n")
        assertFalse("Debug text in learner UI: $copy",forbidden.containsMatchIn(copy))
    }
    private fun back() { automation.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK);SystemClock.sleep(350) }
    private fun snapshot(name:String) {
        val image=automation.takeScreenshot() ?: return
        val folder=File(instrumentation.targetContext.getExternalFilesDir(null),"learner-flow-checks").apply { mkdirs() }
        File(folder,"$name.png").outputStream().use { image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it) };image.recycle()
    }
}

package com.team96.speakeasy.journey

import android.content.Intent
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.team96.speakeasy.LetterUiTestActivity
import com.team96.speakeasy.LetterLargeFontUiTestActivity
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

/** DEC-053/054: real rendered states and isolated persistence, no microphone/child progress writes. */
@RunWith(AndroidJUnit4::class)
class TamilAlphabetInstrumentedTest {
    private val instrumentation get()=InstrumentationRegistry.getInstrumentation()
    private val automation get()=instrumentation.uiAutomation
    @Before fun wakeDisplay(){ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand("input keyevent KEYCODE_WAKEUP")).use{it.readBytes()}}
    private fun host(screen:String="",letter:String?=null,group:String="UYIR",count:Int=0):ActivityScenario<LetterUiTestActivity>{
        val intent=Intent(instrumentation.targetContext,LetterUiTestActivity::class.java).putExtra("screen",screen).putExtra("letter",letter).putExtra("group",group).putExtra("completed",count).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        return ActivityScenario.launch(intent)
    }
    private fun find(value:String,description:Boolean=false):AccessibilityNodeInfo?{
        // Scroll changes can leave cached virtual-node visibility/bounds stale.
        if(android.os.Build.VERSION.SDK_INT>=33)automation.clearCache()
        val root=automation.rootInActiveWindow?:return null
        // Compose exposes virtual semantic children; search that tree directly.
        val pending=java.util.ArrayDeque<AccessibilityNodeInfo>()
        pending.add(root)
        var visited=0
        while(pending.isNotEmpty()&&visited++<5000){
            val node=pending.removeFirst()
            val match=if(description)node.contentDescription?.toString()==value else node.text?.toString()==value
            if(match)return node
            repeat(node.childCount){i->node.getChild(i)?.let{pending.add(it)}}
        }
        return null
    }
    private fun waitFor(value:String,description:Boolean=false):AccessibilityNodeInfo{
        val end=SystemClock.elapsedRealtime()+10000
        do{val node=find(value,description);if(node!=null)return node;SystemClock.sleep(100)}while(SystemClock.elapsedRealtime()<end)
        error("Expected static learning control absent: $value")
    }
    private fun click(value:String,description:Boolean=false){
        var node:AccessibilityNodeInfo?=waitFor(value,description)
        while(node!=null&&!node.isClickable)node=node.parent
        check(node?.performAction(AccessibilityNodeInfo.ACTION_CLICK)==true)
    }
    private fun scrollTo(value:String,description:Boolean=false){
        repeat(12){
            if(find(value,description)?.isVisibleToUser==true)return
            val pending=java.util.ArrayDeque<AccessibilityNodeInfo>()
            automation.rootInActiveWindow?.let{pending.add(it)}
            var scrolled=false
            while(pending.isNotEmpty()){
                val node=pending.removeFirst()
                if(node.isScrollable && node.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)){scrolled=true;break}
                repeat(node.childCount){i->node.getChild(i)?.let{pending.add(it)}}
            }
            if(!scrolled){
                // Some Compose virtual scroll nodes omit the legacy isScrollable flag.
                val screen=checkNotNull(automation.takeScreenshot())
                val x=screen.width/2;val start=screen.height*55/100;val end=screen.height*25/100
                screen.recycle()
                ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand("input swipe $x $start $x $end 300")).use{it.readBytes()}
            }
            SystemClock.sleep(350)
        }
        error("Static control remains outside viewport: $value")
    }
    @Test fun dec053SequentialPracticeUnlocksThenOffersVoluntaryBreak(){
        host().use{
            waitFor("Locked letter ஆ",true)
            click("Open letter அ",true)
            waitFor("Practice complete")
            click("Practice complete")
            waitFor("Uyir · Level 2")
            click("Practice complete");waitFor("Uyir · Level 3")
            click("Practice complete")
            waitFor("Take your time.")
            scrollTo("Continue when ready");waitFor("Continue when ready")
            // DEC065/PRS008: the earned sticker makes the existing scrollable break card taller.
            scrollTo("End session")
            click("End session")
            waitFor("Your practice is saved.")
            waitFor("3 new letter practice marks")
        }
    }
    @Test fun dec053LockedAndUnknownRoutesCannotOpenOrScore(){
        host(letter="TA_LETTER_UYIR_02").use{waitFor("Level locked");assertNull(find("Practice complete"))}
        host(letter="TA_LETTER_UNKNOWN").use{waitFor("Letter unavailable");assertNull(find("Practice complete"))}
    }
    @Test fun dec052CompoundFamilyUsesCorrectVowelAndRetainsAvatar(){
        host(group="UYIRMEI",count=42).use{
            click("Open family க்",true);scrollTo("Open letter கௌ",true);click("Open letter கௌ",true)
            waitFor("Uyirmei · Level 43")
            scrollTo("க் + ஔ = கௌ")
            waitFor("க் + ஔ = கௌ")
            scrollTo("You can listen, look or trace before you speak.")
            waitFor("You can listen, look or trace before you speak.")
            waitFor("Example");waitFor("Microphone loading",true)
        }
    }
    @Test fun dec054RecreationPreservesMarksAndOffersResume(){
        host(letter="TA_LETTER_UYIR_01").use{scenario->
            click("Practice complete")
            waitFor("Uyir · Level 2")
            scenario.recreate()
            waitFor("Take your time.")
            click("Continue when ready")
            waitFor("Uyir · Level 2")
            waitFor("Practice complete")
        }
    }
    @Test fun dec054LargeTextKeepsStopVisible(){
        val intent=Intent(instrumentation.targetContext,LetterLargeFontUiTestActivity::class.java).putExtra("letter","TA_LETTER_UYIR_01").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ActivityScenario.launch<LetterLargeFontUiTestActivity>(intent).use{
            waitFor("Uyir · Level 1")
            SystemClock.sleep(450)
            val stop=waitFor("Break / Stop")
            val bounds=android.graphics.Rect();stop.getBoundsInScreen(bounds)
            assertTrue(stop.isVisibleToUser)
            assertFalse("Stop text must have a visible non-empty rectangle",bounds.isEmpty)
            val screenshot=checkNotNull(automation.takeScreenshot())
            assertTrue("Stop bounds $bounds exceed physical screen ${screenshot.width}x${screenshot.height}",bounds.top>=0 && bounds.bottom<=screenshot.height)
            assertTrue(bounds.left>=0 && bounds.right<=screenshot.width)
            waitFor("Practice complete")
            java.io.File(instrumentation.targetContext.cacheDir,"letter-ui-large-font.png").outputStream().use{out->check(screenshot.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out))}
            screenshot.recycle()
        }
    }
    @Test fun dec055LargeTextWordVoiceKeepsMicAndStopVisible(){
        val intent=Intent(instrumentation.targetContext,LetterLargeFontUiTestActivity::class.java).putExtra("screen","word").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ActivityScenario.launch<LetterLargeFontUiTestActivity>(intent).use{
            waitFor("Word practice")
            scrollTo("Microphone loading",true)
            SystemClock.sleep(450)
            val stop=waitFor("Break / Stop")
            val bounds=android.graphics.Rect();stop.getBoundsInScreen(bounds)
            val screenshot=checkNotNull(automation.takeScreenshot())
            java.io.File(instrumentation.targetContext.cacheDir,"word-ui-font-safety-before.png").outputStream().use{out->screenshot.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out)}
            assertFalse("Word Stop text must have a visible non-empty rectangle: $bounds",bounds.isEmpty)
            assertTrue("Word Stop bounds $bounds exceed physical screen",stop.isVisibleToUser && bounds.top>=0 && bounds.bottom<=screenshot.height)
            java.io.File(instrumentation.targetContext.cacheDir,"word-ui-large-font.png").outputStream().use{out->check(screenshot.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out))}
            screenshot.recycle()
        }
    }
    @Test fun dec056LetterAdvanceReturnsToNewTargetAtLargeText(){
        val intent=Intent(instrumentation.targetContext,LetterLargeFontUiTestActivity::class.java).putExtra("letter","TA_LETTER_UYIR_01").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ActivityScenario.launch<LetterLargeFontUiTestActivity>(intent).use{
            waitFor("Uyir · Level 1");scrollTo("Microphone loading",true)
            click("Practice complete")
            assertTrue(waitFor("Uyir · Level 2").isVisibleToUser)
        }
    }
    private fun assertReadableTarget(symbol:String){
        var node=waitFor(symbol);val bounds=android.graphics.Rect();node.getBoundsInScreen(bounds)
        val density=instrumentation.targetContext.resources.displayMetrics.density
        val settledBy=SystemClock.elapsedRealtime()+5000
        while((!node.isVisibleToUser || bounds.height()<72*density) && SystemClock.elapsedRealtime()<settledBy){
            SystemClock.sleep(100);node=find(symbol)?:node;node.getBoundsInScreen(bounds)
        }
        assertTrue("Whole letter must be readable before practice: $symbol $bounds",node.isVisibleToUser && bounds.height()>=72*density)
        val caption=waitFor("Listen, practise and take your time.")
        assertTrue("Learning guidance must be visible",caption.isVisibleToUser)
    }
    @Test fun dec056WholeLetterIsVisibleOnEntryAndAdvanceAtBothTextSizes(){
        host(letter="TA_LETTER_UYIR_01").use{assertReadableTarget("அ");click("Practice complete");assertReadableTarget("ஆ")}
        val intent=Intent(instrumentation.targetContext,LetterLargeFontUiTestActivity::class.java).putExtra("letter","TA_LETTER_UYIR_01").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        ActivityScenario.launch<LetterLargeFontUiTestActivity>(intent).use{assertReadableTarget("அ");click("Practice complete");assertReadableTarget("ஆ")}
    }
    @Test fun dec056SessionContinuesAcrossLetterCategories(){
        for((id,count,expected) in listOf(Triple("TA_LETTER_UYIR_12",11,"Mei · Level 13"),Triple("TA_LETTER_MEI_18",29,"Aytham · Level 31"),Triple("TA_LETTER_AYTHAM_01",30,"Uyirmei · Level 32"))){
            host(letter=id,count=count).use{click("Practice complete");waitFor(expected)}
        }
    }
    @Test fun dec056ReplayContinuesLocallyWithoutUnlockingAnotherFrontier(){
        host(letter="TA_LETTER_UYIR_01",count=20).use{
            waitFor("Example");waitFor("Microphone loading",true)
            click("Practice complete")
            waitFor("Uyir · Level 2")
            click("Break / Stop");click("End session")
            waitFor("0 new letter practice marks")
        }
    }
    @Test fun dec056EveryLetterKindSharesVoiceControlsAndLastLevelCanFinish(){
        for((id,count) in listOf("TA_LETTER_MEI_01" to 12,"TA_LETTER_AYTHAM_01" to 30,"TA_LETTER_UYIRMEI_18_12" to 246)){
            host(letter=id,count=count).use{
                waitFor("Example");waitFor("Microphone loading",true);waitFor("Practice complete");waitFor("Break / Stop")
                if(count==246){click("Practice complete");waitFor("Your practice is saved.");waitFor("1 new letter practice marks")}
            }
        }
    }
    @Test fun dec053PrivateStorePersistsAndIsolatesProfiles(){
        val context=instrumentation.targetContext
        val first=letterProfileScope(UUID.randomUUID().toString(),"isolated-verification")
        val second=letterProfileScope(UUID.randomUUID().toString(),"isolated-verification")
        val prefs=context.getSharedPreferences("vaakmitra_letter_journey_v1",0)
        try{
            val store=LetterJourneyStore(context,first)
            assertEquals(0,store.load().progress.completedCount)
            assertEquals(1,store.complete(TamilAlphabet.all[0].id).progress.completedCount)
            assertEquals(1,LetterJourneyStore(context,first).load().progress.completedCount)
            assertEquals(1,store.complete(TamilAlphabet.all[0].id).progress.completedCount)
            assertEquals(1,store.complete(TamilAlphabet.all[2].id).progress.completedCount)
            assertEquals(0,LetterJourneyStore(context,second).load().progress.completedCount)
            store.saveSettings(LetterPracticeSettings(1,false))
            assertEquals(LetterPracticeSettings(1,false),LetterJourneyStore(context,first).load().settings)
        }finally{
            val edit=prefs.edit()
            for(scope in listOf(first,second))for(key in listOf("version","completed","round","rewards"))edit.remove("${scope}_$key")
            check(edit.commit())
        }
    }
    @Test fun dec053ExistingWordAvatarExampleAndMicControlsRemain(){
        host(screen="word").use{
            scrollTo("அம்மா");waitFor("அம்மா");waitFor("Example");waitFor("Microphone loading",true);waitFor("Break / Stop")
        }
    }
}

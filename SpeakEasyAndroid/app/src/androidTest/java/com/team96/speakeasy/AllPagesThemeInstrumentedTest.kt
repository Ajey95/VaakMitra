package com.team96.speakeasy
import android.content.Intent
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.compose.ui.graphics.asAndroidBitmap
import com.team96.speakeasy.ui.components.drawWordExample
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
/** DEC057: actual production page views with public fixtures; no saves/login or real microphone. */
@RunWith(AndroidJUnit4::class)
class AllPagesThemeInstrumentedTest {
 @Test fun dec066CurrentRoundCreditsSurviveRecreationWithoutReplayingIndividualCheers(){
  launch("interest-trains").use{scene->
   repeat(2){click("Picture: Amma");assertNull(find("Hear again"));click("இன்னும் · More")}
   scene.onActivity{it.recreate()};interestWait("Break time");click("Continue");click("Picture: Amma")
   interestWait("Your round stamp");interestWait("Public preview · automatic cheer")
  }
 }
 @Test fun dec066LastWordCompletesItsEarnedRoundBeforeQuietSummary(){
  launch("word-terminal-round").use{scene->
   interestWait("Predicted sounds");click("Next word");interestWait("Your round stamp");interestWait("Public preview · automatic cheer")
   assertNull(find("Continue"));click("End session");interestWait("Session summary");assertNoAutomaticReward()
   scene.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 /** DEC066 review fix: the final three manual letters earn a round before the progress-only summary. */
 @Test fun dec066FinalLetterRoundIsNotSkippedByCurriculumCompletion(){
  val letters=com.team96.speakeasy.journey.TamilAlphabet.all
  val intent=Intent(instrumentation.targetContext,LetterUiTestActivity::class.java).putExtra("completed",244).putExtra("letter",letters[244].id)
  androidx.test.core.app.ActivityScenario.launch<LetterUiTestActivity>(intent).use{
   repeat(3){click("Practice complete");if(it<2)interestWait(letters[245+it].symbol)}
   interestWait("Your round stamp");interestWait("Public preview · automatic cheer");assertNull(find("Continue when ready"))
   click("End session");interestWait("Your practice is saved.");interestWait("3 new letter practice marks");assertNull(find("Hear again"))
  }
 }
 /** DEC066/PRS009: passive demonstrations never award completion or start the actor/cheer. */
 @Test fun dec066ShowTheActionStaysQuietAndDoesNotCompleteTurns(){
  launch("context-vendum").use{scene->
   repeat(3){click("Show the action");interestWait("Example explored");SystemClock.sleep(250)
    assertNoAutomaticReward();assertNull(find("Break time"))
    if(it<2)click("See it again")
   }
   val image=fixtureWindow(scene);saveGuideFrame(image,"round-quiet-action.png");image.recycle()
   click("போதும் · Enough");interestWait("Session summary");assertNull(find("Your practice stamp"));assertNull(find("Public preview · automatic cheer"))
  }
 }
 /** DEC066: the shared recorded-result paths stay quiet for words and letters, including rewards ON. */
 @Test fun dec066SingleWordAndLetterRecordingResultsHaveNoCelebration(){
  for(page in listOf("word-result","letter-result-on"))launch(page).use{scene->
   interestWait(if(page=="word-result")"Predicted sounds" else "Practice complete");SystemClock.sleep(300)
   assertNoAutomaticReward()
   if(page=="word-result"){val image=fixtureWindow(scene);saveGuideFrame(image,"round-quiet-mic-result.png");image.recycle()}
  }
 }
 private fun assertNoAutomaticReward(){
  for(attempt in 0 until 10){
   assertNull(find("Tamil reward companion in a veshti and cooling glasses"));assertNull(find("Hear again"));assertNull(find("Public preview · automatic cheer"))
   val pending=java.util.ArrayDeque<AccessibilityNodeInfo>();automation.rootInActiveWindow?.let{pending.add(it)};var scroll:AccessibilityNodeInfo?=null
   while(pending.isNotEmpty()&&scroll==null){val node=pending.removeFirst();if(node.isScrollable&&node.isVisibleToUser)scroll=node else repeat(node.childCount){node.getChild(it)?.let{pending.add(it)}}}
   if(scroll?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)!=true)return
   SystemClock.sleep(150)
  }
 }
 /** DEC065/066: only the completed three-turn round earns the sticker, with no replay tap. */
 @Test fun dec065CompletionAutomaticallyShowsVeshtiRewardAndKeepsControls(){
  launch("interest-trains").use{scene->
   repeat(3){click("Picture: Amma");if(it<2){assertNull(find("Hear again"));click("இன்னும் · More")}}
   interestWait("Your round stamp");interestWait("Public preview · automatic cheer")
   interestWait("Tamil reward companion in a veshti and cooling glasses")
   interestWait("Hear again");interestWait("Stop cheer")
   val picture=fixtureWindow(scene);saveGuideFrame(picture,"veshti-completion.png");picture.recycle()
   scene.onActivity{assertEquals(0,it.previewReportWrites)}
  }
  launch("rewards",true).use{scene->
   interestWait("Tamil reward companion in a veshti and cooling glasses")
   interestWait("Stop cheer")
   val picture=fixtureWindow(scene);saveGuideFrame(picture,"veshti-rewards-2x.png");picture.recycle()
  }
 }
 @Test fun dec066CompletedRoundKeepsStickerCaptionAndStopAtDoubleText(){
  launch("interest-trains",true).use{scene->
   repeat(3){click("Picture: Amma");if(it<2)click("இன்னும் · More")}
   interestWait("Your round stamp");interestWait("Public preview · automatic cheer");interestWait("Tamil reward companion in a veshti and cooling glasses")
   val image=fixtureWindow(scene);saveGuideFrame(image,"round-earned-2x.png");image.recycle()
   click("Stop cheer");interestWait("Cheer stopped");click("Continue");interestWait("Break / Stop");assertNull(find("Hear again"))
  }
 }
 private fun liveGuidePixels(frame:android.graphics.Bitmap,color:Int,left:Float,top:Float,right:Float,bottom:Float):Int{
  var hair=frame.height
  for(y in 0 until frame.height){for(x in 0 until frame.width)if(frame.getPixel(x,y)==0xFF2B2032.toInt()){hair=y;break};if(hair<frame.height)break}
  check(hair<frame.height){"Live guide hair anchor missing"}
  val sx=frame.width/320f;val sy=frame.height/390f;var count=0
  for(y in (hair+(top-35f)*sy).toInt().coerceIn(0,frame.height) until (hair+(bottom-35f)*sy).toInt().coerceIn(0,frame.height))for(x in (left*sx).toInt().coerceIn(0,frame.width) until (right*sx).toInt().coerceIn(0,frame.width))if(frame.getPixel(x,y)==color)count++
  return count
 }
 private fun saveGuideFrame(frame:android.graphics.Bitmap,name:String){java.io.File(instrumentation.targetContext.cacheDir,name).outputStream().use{frame.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}}
 @Test fun dec026LiveGuideNaturallyBlinks(){normalEmulatorMotion{launch("avatars").use{scene->
  interestWait("LIVE PREVIEW");guideFrame(scene).recycle();click("Hello");var largest=0;var smallest=Int.MAX_VALUE;val started=SystemClock.elapsedRealtime();val captured=mutableListOf<Long>()
  repeat(40){index->val frame=guideFrame(scene,settle=false);captured.add(SystemClock.elapsedRealtime()-started);try{
   saveGuideFrame(frame,"motion-live-${index.toString().padStart(2,'0')}.png")
   val white=liveGuidePixels(frame,android.graphics.Color.WHITE,116f,130f,206f,170f)
   if(white>largest){largest=white;saveGuideFrame(frame,"motion-eyes-open.png")}
   if(white<smallest){smallest=white;saveGuideFrame(frame,"motion-eyes-blink.png")}
  }finally{frame.recycle()};SystemClock.sleep(60)}
  java.io.File(instrumentation.targetContext.cacheDir,"motion-live-timing.txt").writeText(captured.joinToString(","))
  android.util.Log.i("VaakMitraMotionTest","PUBLIC blink whiteMax=$largest whiteMin=$smallest")
  assertTrue("The idle guide never visibly blinks: $smallest/$largest",largest>100&&smallest<largest*.7f)
 }}}
 @Test fun dec026LiveGuideGreetsOnceAndReturnsToRest(){normalEmulatorMotion{launch("avatars").use{scene->
  interestWait("LIVE PREVIEW");guideFrame(scene).recycle();click("Hello");var most=0
  repeat(30){val frame=guideFrame(scene,settle=false);try{
   val skin=liveGuidePixels(frame,0xFFB96F49.toInt(),280f,274f,316f,328f)
   if(skin>most){most=skin;saveGuideFrame(frame,"motion-greeting.png")}
  }finally{frame.recycle()};SystemClock.sleep(70)}
  assertTrue("The guide never gives its greeting gesture: $most",most>100)
  SystemClock.sleep(500);val rest=guideFrame(scene,settle=false);try{val skin=liveGuidePixels(rest,0xFFB96F49.toInt(),280f,274f,316f,328f);android.util.Log.i("VaakMitraMotionTest","PUBLIC greeting peak=$most rest=$skin");saveGuideFrame(rest,"motion-greeting-rest.png");assertEquals("Greeting does not settle to rest",0,skin)}finally{rest.recycle()}
 }}}

 /** DEC-026/AVT-005: capture only the public fixture's live avatar, not another window. */
 private fun guideFrame(scene:GalleryScene,settle:Boolean=true):android.graphics.Bitmap{
  // The live guide and its catalogue thumbnail deliberately share an identity label.
  // Return to the top, then choose the widest matching canvas, never a clipped thumbnail.
  if(settle){for(attempt in 0 until 20){
   if(android.os.Build.VERSION.SDK_INT>=33)automation.clearCache()
   val queue=java.util.ArrayDeque<AccessibilityNodeInfo>();automation.rootInActiveWindow?.let{queue.add(it)};var scroll:AccessibilityNodeInfo?=null
   while(queue.isNotEmpty()&&scroll==null){val node=queue.removeFirst();if(node.isScrollable&&node.isVisibleToUser)scroll=node else repeat(node.childCount){node.getChild(it)?.let{queue.add(it)}}}
   if(scroll?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)!=true)break
   SystemClock.sleep(180)
  }
  SystemClock.sleep(180)}
  if(android.os.Build.VERSION.SDK_INT>=33)automation.clearCache()
  val queue=java.util.ArrayDeque<AccessibilityNodeInfo>();automation.rootInActiveWindow?.let{queue.add(it)};val candidates=mutableListOf<android.graphics.Rect>()
  while(queue.isNotEmpty()){
   val node=queue.removeFirst()
   if(node.contentDescription?.toString()=="Meera, idle practice guide"&&node.isVisibleToUser){val bounds=android.graphics.Rect();node.getBoundsInScreen(bounds);candidates.add(bounds)}
   repeat(node.childCount){node.getChild(it)?.let{queue.add(it)}}
  }
  val bounds=checkNotNull(candidates.maxByOrNull{it.width()}){"Live guide is not visible"}
  val full=fixtureWindow(scene)
  try{return android.graphics.Bitmap.createBitmap(full,bounds.left.coerceAtLeast(0),bounds.top.coerceAtLeast(0),bounds.width().coerceAtMost(full.width-bounds.left.coerceAtLeast(0)),bounds.height().coerceAtMost(full.height-bounds.top.coerceAtLeast(0)))}finally{full.recycle()}
 }
 @Test fun dec026GentleHasVisibleMovementRatherThanAnAlmostStaticShift(){normalEmulatorMotion{launch("avatars").use{scene->
  interestWait("LIVE PREVIEW");SystemClock.sleep(600);val positions=mutableListOf<Int>();var width=0
  repeat(9){val frame=guideFrame(scene);try{width=frame.width;var top=frame.height;for(y in 0 until frame.height)for(x in 0 until frame.width)if(frame.getPixel(x,y)==0xFF2B2032.toInt()){top=minOf(top,y);break};assertTrue(top<frame.height);positions.add(top)}finally{frame.recycle()};if(it<8)SystemClock.sleep(600)}
  assertTrue("Gentle movement is barely visible: $positions / width $width",positions.max()-positions.min()>=width*.0125f)
 }}}
 @Test fun dec026StillStopsEveryPreviewBodyAnimation(){normalEmulatorMotion{launch("avatars").use{scene->
  click("Still");interestWait("Still movement");interestWait("LIVE PREVIEW");SystemClock.sleep(700);val first=guideFrame(scene)
  java.io.File(instrumentation.targetContext.cacheDir,"motion-still-first.png").outputStream().use{first.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
  try{repeat(3){SystemClock.sleep(700);val next=guideFrame(scene);try{java.io.File(instrumentation.targetContext.cacheDir,"motion-still-next.png").outputStream().use{next.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};assertTrue("Still mode keeps breathing",first.sameAs(next))}finally{next.recycle()}}}finally{first.recycle()}
 }}}
 @Test fun dec026MovementChoicesExposeSelectionAtDoubleText(){launch("avatars",true).use{
  for(mode in listOf("Still","Reduced","Gentle")){
   click(mode)
   val deadline=SystemClock.elapsedRealtime()+5000;var confirmed=false
   do{
    interestWait(mode)
    var radio:AccessibilityNodeInfo?=find(mode)
    while(radio!=null&&!radio.isCheckable)radio=radio.parent
    confirmed=radio?.isChecked==true
    if(!confirmed)SystemClock.sleep(100)
   }while(!confirmed&&SystemClock.elapsedRealtime()<deadline)
   assertTrue("Chosen movement must expose a checked radio: $mode",confirmed)
   var checked=0
   for(label in listOf("Still","Reduced","Gentle")){
    // At double text, inspect each radio after bringing it into the viewport.
    interestWait(label)
    var radio:AccessibilityNodeInfo?=find(label)
    while(radio!=null&&!radio.isCheckable)radio=radio.parent
    assertNotNull("Movement must expose a radio: $label",radio)
    assertEquals("Wrong checked state: $label after $mode",label==mode,radio!!.isChecked)
    if(radio.isChecked)checked++
   }
   assertEquals("Exactly one movement is selected",1,checked)

  }
  click("Use this guide")
 }}

 @Test fun dec064LetterResultRespectsRewardOptOut(){
  launch("letter-result-off").use{interestWait("Practice complete");assertNull(find("Practice encouragement"));assertNull(find("Hear again"))}
  launch("letter-result-on").use{interestWait("Practice complete");assertNull(find("Practice encouragement"));assertNull(find("Hear again"));assertNull(find("Public preview · automatic cheer"))}
 }

 @Test fun dec064EmptyMoreTurnsOfferABreakWithoutAnEarnedRoundStamp(){
  launch("interest-trains").use{click("இன்னும் · More");click("இன்னும் · More");click("இன்னும் · More");interestWait("Break time");assertNull(find("Your round stamp"))}
 }
 @Test fun dec064WrongChoiceSupportBreakDoesNotAwardARoundStamp(){
  launch("interest-trains").use{click("Picture: Appa");click("Picture: Appa");interestWait("Break time");assertNull(find("Your round stamp"))}
 }
 @Test fun dec063ThirdWordTurnAutomaticallyAppreciatesTheRound(){
  launch("interest-trains").use{
   click("Picture: Amma");assertNull(find("Hear again"));click("இன்னும் · More")
   click("Picture: Amma");click("இன்னும் · More");click("Picture: Amma")
   interestWait("Break time");interestWait("Your round stamp");interestWait("Public preview · automatic cheer")
  }
 }
 @Test fun dec063StoppedCheerDoesNotReplayAfterRecreationAndResume(){
  launch("interest-trains").use{scenario->
   repeat(3){click("Picture: Amma");if(it<2)click("இன்னும் · More")}
   interestWait("Public preview · automatic cheer");click("Stop cheer");interestWait("Cheer stopped")
   scenario.onActivity{it.recreate()};SystemClock.sleep(500);interestWait("Break time");click("Continue");interestWait("Break / Stop");assertNull(find("Hear again"))
   SystemClock.sleep(400);assertNull(find("Public preview · automatic cheer"))
  }
 }
 @Test fun dec063CheerSoundAndMotionOptOutAreLabelledAtDoubleText(){
  launch("rewards",true).use{scenario->
   click("Cheer settings");click("Automatic spoken cheers");click("Celebration motion");click("Calm guide");click("Preview this cheer");interestWait("Public preview · no sound played");click("Save cheers")
   interestWait("Cheer style: Calm guide");click("Cheer settings");interestWait("Automatic spoken cheers");interestWait("Celebration motion")
   val speech=find("Automatic spoken cheers",action=true);val motion=find("Celebration motion",action=true)
   assertNotNull(speech);assertNotNull(motion);assertFalse(speech!!.isChecked);assertFalse(motion!!.isChecked)
   val image=fixtureWindow(scenario,ownedDialog=true);java.io.File(instrumentation.targetContext.cacheDir,"praise-settings-2x.png").outputStream().use{image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};image.recycle()
   click("Cancel")
  }
 }
 @Test fun dec066SinglePictureKeepsQuietFeedback(){
  launch("interest-trains").use{scenario->click("Picture: Amma");interestWait("Picture matched");assertNoAutomaticReward();scenario.onActivity{assertEquals(0,it.previewReportWrites)}}
 }
 @Test fun dec066SessionSummaryDoesNotRepeatCelebration(){
  launch("interest-trains").use{click("Picture: Amma");click("போதும் · Enough");interestWait("Session summary");assertNull(find("Your practice stamp"));assertNoAutomaticReward()}
 }
 @Test fun dec066OnlyTheThirdLetterCompletionCelebratesRound(){
  val intent=Intent(instrumentation.targetContext,LetterUiTestActivity::class.java).putExtra("letter","TA_LETTER_UYIR_01")
  androidx.test.core.app.ActivityScenario.launch<LetterUiTestActivity>(intent).use{
   click("Practice complete");interestWait("Uyir · Level 2");assertNull(find("Hear again"));assertNull(find("Public preview · automatic cheer"))
   click("Practice complete");interestWait("Uyir · Level 3");click("Practice complete");interestWait("Your round stamp");interestWait("Public preview · automatic cheer")
  }
 }
 /** DEC062/PRS001..006: public/inert rewards never create account stars or record audio. */
 @Test fun dec062RewardsOfferNamedCheerStylesWithoutInventingStars(){
  launch("rewards").use{scenario->
   interestWait("Your encouragement");click("Cheer settings");interestWait("Calm guide");interestWait("Little hero");click("Playful friend");click("Save cheers")
   interestWait("Cheer style: Playful friend");click("Play sample");SystemClock.sleep(250);interestWait("Public preview · no sound played");interestWait("0 account stars")
   val image=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"praise-settings.png").outputStream().use{image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};image.recycle()
   scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec062EffortFeedbackKeepsStopAtDoubleText(){
  launch("interest-trains",true).use{scenario->
   click("Picture: Amma");interestWait("Picture matched");assertNoAutomaticReward();interestWait("Break / Stop")
   val image=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"praise-word-2x.png").outputStream().use{image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};image.recycle()
   click("Break / Stop");interestWait("Break time");interestWait("End session");scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec062EmptySummaryHasNoEarnedPracticeStamp(){launch("summary").use{interestWait("No session recorded yet");assertNull(find("Your practice stamp"));assertNull(find("Hear again"))}}
 @Test fun dec066ParticipatingSummaryKeepsProgressWithoutReward(){
  launch("interest-trains").use{scenario->
   click("Picture: Amma");click("போதும் · Enough");interestWait("Session summary");assertNull(find("Your practice stamp"));assertNoAutomaticReward()
   val image=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"praise-summary.png").outputStream().use{image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};image.recycle()
   scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 private fun rendered(art:com.team96.speakeasy.journey.WordArt,active:Boolean):IntArray{
  val bitmap=androidx.compose.ui.graphics.ImageBitmap(120,90);val canvas=androidx.compose.ui.graphics.Canvas(bitmap)
  androidx.compose.ui.graphics.drawscope.CanvasDrawScope().draw(androidx.compose.ui.unit.Density(1f),androidx.compose.ui.unit.LayoutDirection.Ltr,canvas,androidx.compose.ui.geometry.Size(120f,90f)){
   drawRect(com.team96.speakeasy.ui.components.HeritagePaper);drawWordExample(art,active)
  }
  val pixels=IntArray(120*90);bitmap.asAndroidBitmap().getPixels(pixels,0,120,0,0,120,90);return pixels
 }
 @Test fun dec061RenderedHandHasFourFingersAndOneThumb(){
  val pixels=rendered(com.team96.speakeasy.journey.WordArt.HAND,false);val skin=0xFFB56F48.toInt()
  for((x,y)in listOf(46 to 28,54 to 22,62 to 22,70 to 22,30 to 40))assertEquals(skin,pixels[y*120+x])
  assertNotEquals("Extra fifth upright digit",skin,pixels[28*120+77])
 }
 @Test fun dec061RequestAcceptanceRecipientAndRefusalHaveDifferentVisibleActions(){
  val art=com.team96.speakeasy.journey.WordArt.entries
  for(kind in art.filter{!com.team96.speakeasy.journey.WordActivityCatalog.matchIds.any{id->com.team96.speakeasy.journey.WordActivityCatalog.art(id)==it}})
   assertFalse("Unchanged example $kind",rendered(kind,false).contentEquals(rendered(kind,true)))
  for(group in listOf(listOf(com.team96.speakeasy.journey.WordArt.REQUEST,com.team96.speakeasy.journey.WordArt.YES,com.team96.speakeasy.journey.WordArt.FOR_ME),listOf(com.team96.speakeasy.journey.WordArt.DECLINE,com.team96.speakeasy.journey.WordArt.NO)))
   for(i in group.indices)for(j in i+1 until group.size)assertFalse("Same action ${group[i]} / ${group[j]}",rendered(group[i],true).contentEquals(rendered(group[j],true)))
 }
 @Test fun dec061BackgroundRestoreKeepsTwoTurnsAndOpenSceneChoices(){
  launch("interest-trains").use{scenario->
   click("இன்னும் · More");click("இன்னும் · More");interestWait("Practice · 2 / 3 turns, then a break");click("Change play scene")
   scenario.onActivity{it.recreate()};SystemClock.sleep(600);interestWait("Break time");click("Continue")
   interestWait("Practice · 2 / 3 turns, then a break");interestWait("Your word stays the same");click("Close scene choices");click("இன்னும் · More");interestWait("Break time")
  }
 }
 @Test fun dec061HandTwoAndThreeChoicesRemainTouchableAtDoubleText(){
  launch("picture-hand",true).use{scenario->
   interestWait("Picture: Kai");click("Picture: Kai");click("இன்னும் · More");click("Picture: Kai");click("இன்னும் · More");click("Picture: Kai")
   interestWait("Break time");click("Continue");click("இன்னும் · More");click("Picture: Kai");interestWait("Your turn");click("இன்னும் · More")
   val food=interestWait("Picture: Unavu");food.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.id);SystemClock.sleep(400)
   val rectangles=listOf("Kai","Thalai","Unavu").map{name->val node=interestWait("Picture: $name");val b=android.graphics.Rect();node.getBoundsInScreen(b);assertTrue("$name actionable: ${nodeDetails(node)}",node.isClickable);assertTrue("$name width $b",b.width()>100);assertTrue("$name height $b",b.height()>100);b}
   for(i in rectangles.indices)for(j in i+1 until rectangles.size)assertFalse(android.graphics.Rect.intersects(rectangles[i],rectangles[j]))
   val image=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"clear-hand-three-2x.png").outputStream().use{image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};image.recycle()
  }
 }
 @Test fun dec061PictureCaptionAndCardPaddingRespondToTaps(){
  launch("interest-trains").use{scenario->
   interestWait("Picture: Amma").performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.id)
   val settleDeadline=SystemClock.elapsedRealtime()+5000;var previous:android.graphics.Rect?=null;var steady=0
   do{SystemClock.sleep(100);val current=android.graphics.Rect();interestWait("Picture: Amma").getBoundsInScreen(current);steady=if(current==previous)steady+1 else 0;previous=current}while(steady<3&&SystemClock.elapsedRealtime()<settleDeadline)
   assertTrue("Picture bounds did not settle before physical touch",steady>=3)
   val picture=interestWait("Picture: Amma");val caption=find("Mother with child");val bounds=android.graphics.Rect()
   if(caption!=null)interestWait("Mother with child").getBoundsInScreen(bounds)else{picture.getBoundsInScreen(bounds);assertTrue(picture.contentDescription?.contains("Mother with child")==true);bounds.top=bounds.bottom-20}
   val now=SystemClock.uptimeMillis();val x=bounds.centerX().toFloat();val y=bounds.centerY().toFloat()
   println("Physical caption tap: picture=${nodeDetails(picture)}; captionFound=${caption!=null}; tap=$x,$y; example=${find("Example")?.let{nodeDetails(it)}}")
   val diagnostic=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"clear-caption-touch.png").outputStream().use{diagnostic.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};diagnostic.recycle()
   val down=android.view.MotionEvent.obtain(now,now,android.view.MotionEvent.ACTION_DOWN,x,y,0);assertTrue(automation.injectInputEvent(down,true));down.recycle()
   val up=android.view.MotionEvent.obtain(now,now+50,android.view.MotionEvent.ACTION_UP,x,y,0);assertTrue(automation.injectInputEvent(up,true));up.recycle()
   interestWait("Picture matched")
  }
 }
 @Test fun dec061FamilyPicturesAndLabelledSceneChooserKeepTheSameWord(){
  launch("interest-trains").use{scenario->
   val mother=interestWait("Picture: Amma");assertTrue(mother.contentDescription?.contains("Mother with child")==true);assertTrue("Mother actionable node: ${nodeDetails(mother)}",mother.isClickable)
   assertTrue(interestWait("Picture: Appa").contentDescription?.contains("Father with child")==true);assertNull(find("Picture: Udhavi"))
   click("Change play scene");interestWait("Your word stays the same");interestWait("Scene: trains");interestWait("Scene: animals");interestWait("Scene: stories")
   val choices=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"clear-scene-choices.png").outputStream().use{choices.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};choices.recycle()
   click("Scene: animals");interestWait("Animal trail");interestWait("அம்மா");assertNull(find("Scene: trains"))
   click("Change play scene");click("Scene: stories");interestWait("Story pages");interestWait("அம்மா");assertNull(find("Picture matched"))
   val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"clear-family-scene.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
   scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec061ContextActionRestoresWithoutInventingAPictureMatch(){
  launch("word-result").use{scenario->
   click("Next word");interestWait("ஆம்");interestWait("Say yes to an offered ball");assertNull(find("Picture: Aam"))
   click("Show the action");interestWait("Example explored");assertNull(find("Picture matched"));assertNull(find("Stop recording"))
   scenario.onActivity{it.recreate()};SystemClock.sleep(600);interestWait("Break time");click("Continue");interestWait("ஆம்");interestWait("Example explored")
   click("போதும் · Enough");interestWait("Session summary");interestWait("Illustrated examples explored: 1. These are activity counts, not speech scores.")
   scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec061VendumUsesARequestSceneInsteadOfRandomPictureAnswers(){
  launch("context-vendum").use{scenario->
   interestWait("Tap Show the action. Speaking is optional.");interestWait("வேண்டும்");interestWait("Ask for the ball");assertNull(find("Picture: Vendum"));click("Show the action");interestWait("Ball offered to the child")
   interestWait("Example explored");interestWait("Break / Stop");assertNull(find("Stop recording"))
   val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"clear-vendum-context.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
   scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec061SceneChoicesRemainNamedAndStopReachableAtDoubleText(){
  launch("interest-trains",true).use{scenario->
   click("Change play scene");interestWait("Scene: animals");click("Scene: animals");SystemClock.sleep(400)
   val deadline=SystemClock.elapsedRealtime()+5000;var shown=false
   do{val scene=find("Animal trail · 0 of 3 turns");val b=android.graphics.Rect();scene?.getBoundsInScreen(b);shown=scene?.isVisibleToUser==true && b.height()>=56*instrumentation.targetContext.resources.displayMetrics.density;if(!shown)SystemClock.sleep(50)}while(!shown && SystemClock.elapsedRealtime()<deadline)
   assertTrue("Chosen scene hidden",shown);interestWait("அம்மா")
   val stop=interestWait("Break / Stop");val bounds=android.graphics.Rect();stop.getBoundsInScreen(bounds)
   scenario.onActivity{activity->val origin=IntArray(2);activity.window.decorView.getLocationOnScreen(origin);assertTrue(bounds.bottom<=origin[1]+activity.window.decorView.height)}
   val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"clear-scenes-2x.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
  }
 }
 @Test fun dec060RecreationKeepsCurrentWordAndSessionCounts(){
  launch("interest-trains").use{scenario->
   click("Picture: Amma");click("Next activity");interestWait("அப்பா");click("Picture: Appa");interestWait("Picture matched")
   scenario.onActivity{it.recreate()};SystemClock.sleep(600);interestWait("Break time");click("Continue")
   interestWait("அப்பா");interestWait("Picture matched");click("போதும் · Enough");interestWait("Session summary")
   interestWait("2 picture matches · 0 without extra picture hints. These are activity counts, not speech scores.")
   interestWait("Session only · not saved on this device");scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec059MoreAndEnoughRequestsWorkWithoutASpeechOrPictureScore(){
  launch("interest-trains").use{scenario->
   interestWait("Train journey");click("இன்னும் · More");interestWait("Follow the picture");assertNull(find("Picture matched"));assertNull(find("Stop recording"))
   click("போதும் · Enough");interestWait("Session summary");scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec059ThreeInterestScenesUseTheSameAvatarAndVoiceControlsOffline(){
  for((page,title)in listOf("interest-trains" to "Train journey","interest-animals" to "Animal trail","interest-stories" to "Story pages"))launch(page).use{scenario->
   interestWait(title);interestWait("Meera");interestWait("Word practice");interestWait("Example");interestWait("Microphone loading");interestWait("Break / Stop")
   click("Picture: Amma");interestWait("Picture matched");scenario.onActivity{assertEquals(0,it.previewReportWrites)}
   val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"$page.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
  }
 }
 @Test fun dec059PictureEvidenceFadesHelpAndCanRestoreItWithoutRecording(){
  launch("interest-trains").use{scenario->
   interestWait("Follow the picture");click("Picture: Amma");click("இன்னும் · More");click("Picture: Amma");interestWait("Match the picture")
   click("இன்னும் · More");click("Picture: Amma");interestWait("Break time");click("Continue");click("இன்னும் · More");click("Picture: Amma");interestWait("Your turn")
   click("இன்னும் · More");click("Show help");interestWait("Follow the picture");assertNull(find("Stop recording"));scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec059WritingPartsStayVisualAndNextActivityRetainsWordRoutes(){
  launch("interest-trains").use{scenario->
   click("Writing parts");interestWait("Writing parts · whole-word audio only");interestWait("ம்");click("Writing parts")
   click("Picture: Amma");click("Next activity");interestWait("அப்பா");interestWait("Meera");interestWait("Microphone loading");click("Break / Stop");interestWait("Break time");click("Continue");interestWait("அப்பா")
   scenario.onActivity{assertEquals(0,it.previewReportWrites)}
  }
 }
 @Test fun dec059WrongPictureRestoresHelpAndNeverStartsAudio(){
  launch("interest-trains").use{
   interestWait("Train journey")
   val wrong=com.team96.speakeasy.journey.learningOptions("TA_WORD_0001",2,0).first{it!="TA_WORD_0001"}
   val word=com.team96.speakeasy.journey.StarterWords.all.first{it.id==wrong}
   click("Picture: ${word.transliteration}");interestWait("Let's look together");interestWait("Follow the picture");assertNull(find("Stop recording"))
  }
 }
 @Test fun dec059LargeTextKeepsInternalActivityAndStopReachable(){
  launch("interest-trains",true).use{scenario->
   interestWait("Break / Stop");val stop=interestWait("Break / Stop");val bounds=android.graphics.Rect();stop.getBoundsInScreen(bounds)
   scenario.onActivity{activity->val origin=IntArray(2);activity.window.decorView.getLocationOnScreen(origin);assertTrue(bounds.bottom<=origin[1]+activity.window.decorView.height)}
   val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"interest-2x.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
  }
 }
 @Test fun dec058PreviewCanRetryAdvanceAcrossFocusedOrderAndFinishWithoutScoring(){
  launch("word-result").use{scenario->waitFor("Predicted sounds");click("Practise again");waitFor("Microphone loading");waitFor("அப்பா");scenario.onActivity{assertEquals(0,it.previewReportWrites)}}
  launch("word-result").use{scenario->waitFor("Predicted sounds");click("Next word");waitFor("ஆம்");waitFor("Microphone loading");scenario.onActivity{assertEquals(0,it.previewReportWrites)}}
  launch("word-result-end").use{scenario->waitFor("Predicted sounds");click("Next word");waitFor("Session summary");scenario.onActivity{assertEquals(0,it.previewReportWrites)}}
 }
 @Test fun dec058FocusedAndFullCatalogueOpenTheSameSafeWordSession(){
  launch("words").use{scenario->
   waitFor("18 words · your familiar session flow");waitFor("Focused practice · 18");click("All words · 25");waitFor("25 words · your familiar session flow");click("Focused practice · 18");waitFor("18 words · your familiar session flow")
   repeat(12){if(find("Enna",action=true)==null){
    val metrics=instrumentation.targetContext.resources.displayMetrics
    ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand("input swipe ${metrics.widthPixels/2} ${metrics.heightPixels*80/100} ${metrics.widthPixels/2} ${metrics.heightPixels*35/100} 250")).use{it.readBytes()};SystemClock.sleep(200)
   }}
   click("Enna");waitFor("Word practice");waitFor("என்ன");waitFor("Microphone loading");tapUnavailableMicrophone();assertNull(find("Stop recording"));scenario.onActivity{assertEquals(0,it.previewReportWrites)}
   val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"focused-enna-session.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
  }
 }
 @Test fun dec058FocusedControlsRemainReachableAtDoubleFont(){
  launch("words",true).use{scenario->waitFor("18 words · your familiar session flow");click("All words · 25");waitFor("25 words · your familiar session flow");click("Focused practice · 18");waitFor("18 words · your familiar session flow");SystemClock.sleep(250)
   val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"focused-2x-list.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
  }
 }
 private val instrumentation get()=InstrumentationRegistry.getInstrumentation()
 private val automation get()=instrumentation.uiAutomation
 private val mainHandler get()=if(android.os.Build.VERSION.SDK_INT>=28)android.os.Handler.createAsync(android.os.Looper.getMainLooper())else android.os.Handler(android.os.Looper.getMainLooper())
 /** Animated guides are valid UI: lifecycle operations must not wait for an animation-free message queue. */
 private inner class GalleryScene:java.io.Closeable{
  private var activity:ThemeGalleryTestActivity?=null
  fun onActivity(action:(ThemeGalleryTestActivity)->Unit){
   val deadline=SystemClock.elapsedRealtime()+10000
   do{
    val ready=java.util.concurrent.CountDownLatch(1);val failure=java.util.concurrent.atomic.AtomicReference<Throwable>();var found=false
    mainHandler.post{
     try{
      val current=androidx.test.runner.lifecycle.ActivityLifecycleMonitorRegistry.getInstance().getActivitiesInStage(androidx.test.runner.lifecycle.Stage.RESUMED).filterIsInstance<ThemeGalleryTestActivity>().singleOrNull()?.takeIf{!it.isDestroyed && it.window.decorView.isAttachedToWindow}
      if(current!=null){activity=current;action(current);found=true}
     }catch(error:Throwable){failure.set(error)}finally{ready.countDown()}
    }
    check(ready.await(15,java.util.concurrent.TimeUnit.SECONDS)){"Gallery main-thread callback timed out"}
    failure.get()?.let{throw it};if(found)return;SystemClock.sleep(100)
   }while(SystemClock.elapsedRealtime()<deadline)
   error("Gallery did not resume")
  }
  override fun close(){
   val ready=java.util.concurrent.CountDownLatch(1)
   mainHandler.post{try{activity?.finish()}finally{ready.countDown()}}
   check(ready.await(5,java.util.concurrent.TimeUnit.SECONDS)){"Gallery finish timed out"}
   val deadline=SystemClock.elapsedRealtime()+10000
   while(activity?.isDestroyed==false&&SystemClock.elapsedRealtime()<deadline)SystemClock.sleep(50)
   check(activity?.isDestroyed!=false){"Gallery did not finish"}
  }
 }
 private fun nodeDetails(node:AccessibilityNodeInfo):String{
  val parts=mutableListOf<String>();var current:AccessibilityNodeInfo?=node
  repeat(4){current?.let{n->val b=android.graphics.Rect();n.getBoundsInScreen(b);parts.add("text=${n.text};desc=${n.contentDescription};click=${n.isClickable};bounds=$b;children=${n.childCount}");current=n.parent}}
  return parts.joinToString(" -> ")
 }
 private fun find(value:String,action:Boolean=false):AccessibilityNodeInfo?{
  if(android.os.Build.VERSION.SDK_INT>=33)automation.clearCache()
  val pending=java.util.ArrayDeque<AccessibilityNodeInfo>();automation.rootInActiveWindow?.let{pending.add(it)}
  var visited=0
  while(pending.isNotEmpty()&&visited++<5000){
   val n=pending.removeFirst()
   if(n.text?.toString()==value||n.contentDescription?.toString()==value||(value.startsWith("Picture: ")&&n.contentDescription?.toString()?.startsWith("$value · ")==true)){
    if(!action)return n
    var target:AccessibilityNodeInfo?=n
    while(target!=null&&!target.isClickable)target=target.parent
    if(target!=null&&target.isEnabled&&target.isVisibleToUser)return target
   }
   repeat(n.childCount){n.getChild(it)?.let{pending.add(it)}}
  };return null
 }
 private fun waitFor(text:String):AccessibilityNodeInfo=interestWait(text)
 private fun scrollVisible(forward:Boolean):Boolean {
  val queue=java.util.ArrayDeque<AccessibilityNodeInfo>();automation.rootInActiveWindow?.let{queue.add(it)}
  var visited=0
  while(queue.isNotEmpty()&&visited++<5000){val node=queue.removeFirst()
   if(node.isScrollable&&node.isVisibleToUser)return node.performAction(if(forward)AccessibilityNodeInfo.ACTION_SCROLL_FORWARD else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)
   repeat(node.childCount){node.getChild(it)?.let{child->queue.add(child)}}
  };return false
 }
 private fun interestWait(text:String):AccessibilityNodeInfo {
  val deadline=SystemClock.elapsedRealtime()+20000;var forward=true
  do{
   find(text)?.let{node->if(node.isVisibleToUser)return node;node.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.id)}
   if(!scrollVisible(forward))forward=!forward
   SystemClock.sleep(100)
  }while(SystemClock.elapsedRealtime()<deadline)
  error("Interest control absent: $text")
 }
 private fun tapUnavailableMicrophone(){
  val microphone=interestWait("Microphone loading")
  assertNull("Public fixtures must never expose an enabled recorder",find("Microphone loading",action=true))
  val bounds=android.graphics.Rect();microphone.getBoundsInScreen(bounds)
  ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand("input tap ${bounds.centerX()} ${bounds.centerY()}")).use{it.readBytes()}
  assertNull(find("Stop recording"))
 }
 private fun click(text:String){
  val deadline=SystemClock.elapsedRealtime()+20000;var forward=true
  do{
   find(text,action=true)?.let{if(it.performAction(AccessibilityNodeInfo.ACTION_CLICK))return}
   find(text)?.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.id)
   if(!scrollVisible(forward))forward=!forward
   SystemClock.sleep(100)
  }while(SystemClock.elapsedRealtime()<deadline)
  error("Visible action not clickable: $text")
 }
 /** DEC057 review R2: copy this app's window surface, never the composited device/notifications. */
 private fun fixtureWindow(scenario:GalleryScene,ownedDialog:Boolean=false):android.graphics.Bitmap{
  fun dialogWindow(view:android.view.View):android.view.Window?{
   if(view is androidx.compose.ui.window.DialogWindowProvider)return view.window
   if(view is android.view.ViewGroup)for(i in 0 until view.childCount)dialogWindow(view.getChildAt(i))?.let{return it}
   return null
  }
  repeat(3){
   val ready=java.util.concurrent.CountDownLatch(1);var result=android.view.PixelCopy.ERROR_UNKNOWN;var picture:android.graphics.Bitmap?=null
   scenario.onActivity{activity->
    val window=if(ownedDialog)android.view.inspector.WindowInspector.getGlobalWindowViews().filter{it.isShown && it.hasWindowFocus()}.mapNotNull{dialogWindow(it)}.singleOrNull() else activity.window
    if(window==null || window.decorView.width<=0 || window.decorView.height<=0){ready.countDown()}else{
     val bitmap=android.graphics.Bitmap.createBitmap(window.decorView.width,window.decorView.height,android.graphics.Bitmap.Config.ARGB_8888);picture=bitmap
     try{android.view.PixelCopy.request(window,bitmap,{status->result=status;ready.countDown()},mainHandler)}catch(_:IllegalArgumentException){ready.countDown()}
    }
   }
   assertTrue("App-window capture timed out",ready.await(5,java.util.concurrent.TimeUnit.SECONDS))
   if(result==android.view.PixelCopy.SUCCESS)return checkNotNull(picture)
   picture?.recycle();SystemClock.sleep(150)
  }
  error("Owned app-window surface unavailable")
 }
 private fun normalEmulatorMotion(block:()->Unit){
  if(android.os.Build.HARDWARE !in setOf("ranchu","goldfish")){block();return}
  val previous=android.provider.Settings.Global.getString(instrumentation.targetContext.contentResolver,android.provider.Settings.Global.ANIMATOR_DURATION_SCALE)
  fun shell(command:String){ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand(command)).use{it.readBytes()}}
  shell("settings put global animator_duration_scale 1")
  try{block()}finally{shell(if(previous==null) "settings delete global animator_duration_scale" else "settings put global animator_duration_scale $previous")}
 }
 @Test fun silentActiveCandleDoesNotAnimateItsDecoration(){normalEmulatorMotion{launch("candle-active").use{scenario->
  waitFor("Candle Game");click("Start Blowing");waitFor("Listening · microphone on");SystemClock.sleep(450)
  val first=fixtureWindow(scenario)
  try{repeat(3){SystemClock.sleep(130);val next=fixtureWindow(scenario);try{assertTrue("Silent input is causing decorative motion",first.sameAs(next))}finally{next.recycle()}}}finally{first.recycle()}
 }}}
 @Test fun publicPracticeCannotRecordPlayOrReplaceAReport(){
  for(page in listOf("word","letter"))launch(page).use{scenario->
   waitFor(if(page=="word")"Word practice" else "Uyir · Level 1");click("Example");tapUnavailableMicrophone();SystemClock.sleep(250)
   assertNull(find("Stop recording"));scenario.onActivity{assertEquals(0,it.previewReportWrites)}
   if(page=="word"){click("Back");waitFor("Session summary");scenario.onActivity{assertEquals(0,it.previewReportWrites)}}
  }
  launch("word").use{scenario->waitFor("Word practice");click("Break / Stop");waitFor("End session");click("End session");waitFor("Session summary");scenario.onActivity{assertEquals(0,it.previewReportWrites)}}
  launch("candle").use{scenario->waitFor("Candle Game");click("Start Blowing");SystemClock.sleep(250);assertNull(find("Listening · microphone on"));scenario.onActivity{assertEquals(0,it.candleProbeStops)}}
 }
 @Test fun unavailableRewardsDoNotBecomeUnconfirmedZeroOrEarned(){
  for(page in listOf("rewards-unknown","rewards","rewards-earned"))launch(page).use{scenario->
   waitFor("Rewards")
   when(page){"rewards-unknown"->{waitFor("Account stars unavailable");assertNull(find("0 account stars"));assertNull(find("Unlocked"))};"rewards"->waitFor("No stars recorded yet. There is no hurry.");else->{waitFor("35 account stars");waitFor("Unlocked")}}
   val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"theme-$page.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
  }
 }
 @Test fun fixturePixelsExcludeOtherWindows(){launch("splash").use{scenario->
  waitFor("VaakMitra");var dialog:android.app.Dialog?=null
  try{scenario.onActivity{activity->dialog=android.app.Dialog(activity).apply{setContentView(android.widget.TextView(activity).apply{text="PUBLIC OVERLAY";setBackgroundColor(android.graphics.Color.MAGENTA)});show();window!!.setLayout(-1,-1)}};SystemClock.sleep(300)
   val picture=fixtureWindow(scenario);assertNotEquals("Screenshot includes another window",android.graphics.Color.MAGENTA,picture.getPixel(picture.width/2,picture.height/2));picture.recycle()
  }finally{scenario.onActivity{dialog?.dismiss()}}
 }}
 @Test fun candleStopStaysVisibleAndReleasesTheFakeInput(){launch("candle-active",true).use{scenario->
  waitFor("Candle Game");click("Start Blowing");waitFor("Listening · microphone on")
  ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand("input swipe 300 250 300 750 300")).use{it.readBytes()};SystemClock.sleep(200)
  val stop=waitFor("Break / Stop");assertTrue(stop.isVisibleToUser);val bounds=android.graphics.Rect();stop.getBoundsInScreen(bounds)
  val activePicture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"theme-candle-listening.png").outputStream().use{activePicture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};activePicture.recycle()
  val viewport=android.graphics.Rect()
  scenario.onActivity{activity->val origin=IntArray(2);activity.window.decorView.getLocationOnScreen(origin);viewport.set(origin[0],origin[1],origin[0]+activity.window.decorView.width,origin[1]+activity.window.decorView.height)}
  android.util.Log.i("VaakMitraThemeEvidence","fake_stop_bounds=$bounds window=$viewport app_metrics_height=${instrumentation.targetContext.resources.displayMetrics.heightPixels}")
  assertTrue("Stop is outside its actual app window: $bounds versus $viewport",viewport.contains(bounds))
  ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand("input tap ${bounds.centerX()} ${bounds.centerY()}")).use{it.readBytes()};waitFor("Start Blowing")
  scenario.onActivity{assertEquals(1,it.candleProbeStops)}
  val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"theme-candle-stop.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
 }}
 @Test fun winningCandleIsStaticAndReleasesTheFakeInput(){normalEmulatorMotion{launch("candle-win").use{scenario->
  waitFor("Candle Game");click("Start Blowing");waitFor("You did it! Candle's out! 🎂")
  SystemClock.sleep(250)
  val first=fixtureWindow(scenario);SystemClock.sleep(300);val second=fixtureWindow(scenario)
  assertTrue("Winning decoration is moving",first.sameAs(second));java.io.File(instrumentation.targetContext.cacheDir,"theme-candle-win.png").outputStream().use{second.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};first.recycle();second.recycle();scenario.onActivity{assertEquals(1,it.candleProbeStops)}
 }}}
 @Test fun endedFakeInputRestoresStartAndCanRetry(){launch("candle-ended").use{scenario->
  waitFor("Candle Game");click("Start Blowing");waitFor("Microphone stopped. Tap Start Blowing to try again.");assertNull(find("Listening · microphone on"))
  val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"theme-candle-error.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
  click("Start Blowing");waitFor("Listening · microphone on");click("Break / Stop");waitFor("Start Blowing");scenario.onActivity{assertEquals(1,it.candleProbeStops)}
 }}
 private val pages=listOf("splash" to "VaakMitra","onboarding" to "Practise Tamil Words","login" to "Welcome to VaakMitra","register" to "Create your account","home" to "VaakMitra","lessons" to "Letters & Words","letters" to "Uyir","letter" to "Uyir · Level 1","word" to "Word practice","avatars" to "Choose their guide","caregiver" to "Build a comfortable plan","profile" to "Profile","progress" to "Practice progress","rewards" to "Rewards","summary" to "Session summary","checkup" to "Therapist checkup","candle" to "Candle Game")
 private fun launch(page:String,large:Boolean=false):GalleryScene{
  ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand("input keyevent KEYCODE_WAKEUP")).use{it.readBytes()}
  val intent=Intent(instrumentation.targetContext,if(large)ThemeGalleryLargeFontTestActivity::class.java else ThemeGalleryTestActivity::class.java).putExtra("page",page).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
  instrumentation.targetContext.startActivity(intent)
  return GalleryScene().apply{onActivity{}}
 }
 @Test fun all17PagesHaveReadablePaperSurfacesAndCapturePublicScreenshots(){
  for((page,title)in pages)launch(page).use{scenario->waitFor(title);SystemClock.sleep(450)
   val picture=fixtureWindow(scenario);val color=picture.getPixel(3,picture.height/2)
   assertTrue("$page still has a dark legacy page",android.graphics.Color.red(color)>225&&android.graphics.Color.green(color)>210&&android.graphics.Color.blue(color)>185)
   java.io.File(instrumentation.targetContext.cacheDir,"theme-$page.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
  }
 }
 @Test fun onboardingKeepsItsThreeStepLoginFlow(){launch("onboarding").use{click("Next");waitFor("Meet Your Guide");waitFor("2 of 3");click("Next");waitFor("Private by Default");waitFor("3 of 3");click("Continue");waitFor("Welcome to VaakMitra")}}
 @Test fun launcherAndPlatformSplashUseTheOwnedBrand(){
  val resources=instrumentation.targetContext.resources
  assertNotEquals(0,resources.getIdentifier("vm_brand_mark","drawable",instrumentation.targetContext.packageName))
  assertNotNull(instrumentation.targetContext.packageManager.getApplicationIcon(instrumentation.targetContext.packageName))
  assertFalse(instrumentation.targetContext.packageManager.getActivityInfo(android.content.ComponentName(instrumentation.targetContext,ThemeGalleryTestActivity::class.java),0).exported)
  if(android.os.Build.VERSION.SDK_INT>=31){
   val theme=resources.newTheme().apply{applyStyle(R.style.Theme_SpeakEasy,true)};val value=android.util.TypedValue()
   assertTrue(theme.resolveAttribute(android.R.attr.windowSplashScreenAnimatedIcon,value,true))
   assertEquals(R.drawable.vm_brand_mark,value.resourceId)
   assertTrue(theme.resolveAttribute(android.R.attr.windowSplashScreenBackground,value,true))
   assertEquals(android.graphics.Color.parseColor("#FFF6E3"),value.data)
  }
 }
 @Test fun largeTextFormsAndGuideKeepTheirActionsReachable(){
  for((page,title,action)in listOf(Triple("login","Welcome to VaakMitra","Start learning"),Triple("register","Create your account","Create account"),Triple("caregiver","Build a comfortable plan","Save plan & choose guide"),Triple("avatars","Choose their guide","Use this guide"),Triple("summary","Session summary","Back home"),Triple("candle","Candle Game","Start Blowing"))){
   launch(page,true).use{scenario->waitFor(title)
    var visible=find(action)?.isVisibleToUser==true
    repeat(15){if(!visible){val metrics=instrumentation.targetContext.resources.displayMetrics;val x=metrics.widthPixels/2;val y=metrics.heightPixels*70/100;val end=metrics.heightPixels*30/100;ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand("input swipe $x $y $x $end 300")).use{it.readBytes()};SystemClock.sleep(350);visible=find(action)?.isVisibleToUser==true}}
    assertTrue("$page action hidden at2x font",visible)
    val picture=fixtureWindow(scenario);java.io.File(instrumentation.targetContext.cacheDir,"theme-2x-$page.png").outputStream().use{picture.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};picture.recycle()
   }
  }
 }
}

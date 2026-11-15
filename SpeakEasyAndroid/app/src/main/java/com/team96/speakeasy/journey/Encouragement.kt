package com.team96.speakeasy.journey

/** DEC062/PRS001..006: a closed original effort vocabulary, never an acoustic assessment. */
enum class PraiseStyle(val wire:String,val title:String,val rate:Float,val pitch:Float){
 CALM("calm","Calm guide",.90f,1f), HERO("hero","Little hero",.98f,.96f), PLAYFUL("playful","Playful friend",1.02f,1.08f);
 companion object{fun from(value:String?)=entries.firstOrNull{it.wire==value}?:HERO}
}
enum class PraiseEvent{PICTURE,EXPLORE,PRACTICE,SESSION,ROUND}
/** DEC066/PRS009: legacy individual/summary cues never become automatic celebrations. */
fun automaticCelebrationEligible(event:PraiseEvent)=event==PraiseEvent.ROUND
/** DEC066: legacy Int credits included passive demos; only tagged attribution survives restore. */
fun roundParticipationSnapshot(count:Int)=listOf(1,count.coerceIn(0,5))
fun restoreRoundParticipation(raw:Any?):Int {
 val parts=raw as? List<*> ?: return 0
 if(parts.size!=2||parts[0]!=1)return 0
 val count=parts[1] as? Int ?: return 0
 return count.takeIf{it in 0..5}?:0
}
data class PraiseSettings(val style:PraiseStyle=PraiseStyle.HERO,val automaticSpeech:Boolean=true,val motion:Boolean=true)

/** DEC063: one ephemeral completion, no queue and no reconstruction from restored progress. */
class PraiseMailbox {
 private var ticket:Pair<String?,String>?=null
 private var claimed=false
 @Synchronized fun issue(owner:String?):String {
  val id=java.util.UUID.randomUUID().toString();ticket=owner to id;claimed=false;return id
 }
 @Synchronized fun issueFor(origin:String?,currentOwner:String?):String?=if(origin==currentOwner)issue(origin)else null
 @Synchronized fun claim(owner:String?,id:String):Boolean {
  val current=ticket?:return false
  if(current.second!=id)return false
  if(current.first!=owner){ticket=null;return false}
  if(claimed)return false
  claimed=true;return true
 }
 @Synchronized fun isCurrent(owner:String?,id:String):Boolean=ticket==(owner to id)
 @Synchronized fun cancel(id:String?){if(id!=null && ticket?.second==id)ticket=null}
 @Synchronized fun clear(){ticket=null}
}

/** One authoritative confirmed value shared by a profile's panels, including ephemeral profiles. */
class PraisePreferenceCache {
 private var identity:String?=null;private var loaded=false
 private var confirmed:ConfirmedPraiseSettings?=null
 @Synchronized fun load(owner:String?,read:()->PraiseSettings):PraiseSettings {
  if(!loaded||identity!=owner){identity=owner;loaded=true;confirmed=ConfirmedPraiseSettings(owner,read())}
  return checkNotNull(confirmed).value
 }
 @Synchronized fun save(origin:String?,current:String?,candidate:PraiseSettings,read:()->PraiseSettings,write:(PraiseSettings)->Boolean):Boolean {
  if(origin!=current)return false
  load(current,read)
  return checkNotNull(confirmed).save(current,candidate){write(candidate)}
 }
}
class SessionFinishGate(private val origin:String?){
 private var started=false
 @Synchronized fun begin(current:String?):Boolean {if(started||origin!=current)return false;started=true;return true}
}
fun hasRecordedSamples(sampleCount:Int)=sampleCount>0
fun recordedPraiseEligible(sampleCount:Int,letter:Boolean,rewards:Boolean)=hasRecordedSamples(sampleCount)&&(!letter||rewards)
fun earnedPraiseRound(reason:LetterPause,participatingTurns:Int,roundSize:Int)=reason==LetterPause.ROUND&&roundSize>=3&&participatingTurns>=roundSize
fun praiseWithinBudget(startMs:Long,nowMs:Long)=nowMs>=startMs&&nowMs-startMs<4000L

fun praiseName(raw:String):String {
 val plain=buildString{raw.codePoints().limit(48).forEach{cp->
  if(Character.isLetter(cp)||Character.getType(cp) in listOf(Character.NON_SPACING_MARK.toInt(),Character.COMBINING_SPACING_MARK.toInt()))appendCodePoint(cp)
  else if(Character.isWhitespace(cp))append(' ')
 }}.trim().replace(Regex(" +")," ")
 return plain.takeUnless{it.equals("Friend",true)||it.equals("Little Star",true)}.orEmpty()
}
fun praiseLine(alias:String,style:PraiseStyle,event:PraiseEvent):String {
 val name=praiseName(alias).let{if(it.isEmpty())"" else "$it, "}
 val activity=when(event){PraiseEvent.PICTURE->"படத்தைக் கண்டுபிடித்தாய்!";PraiseEvent.EXPLORE->"படத்துடன் பயிற்சி செய்தாய்!";PraiseEvent.PRACTICE->"நல்ல முயற்சி!";PraiseEvent.SESSION->"இன்றைய பயிற்சி அருமை!";PraiseEvent.ROUND->"பயிற்சி சுற்றை முடித்தாய்!"}
 return name+when(style){PraiseStyle.CALM->"அருமையான முயற்சி. $activity";PraiseStyle.HERO->"நீ ஒரு குட்டி ஹீரோ! $activity";PraiseStyle.PLAYFUL->"சூப்பர்! அசத்தல் முயற்சி! $activity"}
}
fun hasPraiseParticipation(report:LocalSessionReport?):Boolean=report?.let{it.attemptCount>0||it.activityChoices>0||it.activityContextTurns>0}?:false

data class PraiseDelivery(val consumed:String?,val play:Boolean)
/** Consume a new event even when quiet/background/busy, so it cannot become a delayed surprise. */
fun consumePraise(last:String?,event:String,foreground:Boolean,optedIn:Boolean,busy:Boolean):PraiseDelivery =
 if(last==event)PraiseDelivery(last,false) else PraiseDelivery(event,foreground&&optedIn&&!busy)

class ConfirmedPraiseSettings(private val owner:String?,initial:PraiseSettings){
 var value=initial;private set
 fun save(currentOwner:String?,candidate:PraiseSettings,commit:()->Boolean):Boolean{
  if(currentOwner!=owner)return false
  if(!runCatching{commit()}.getOrDefault(false))return false
  value=candidate;return true
 }
}

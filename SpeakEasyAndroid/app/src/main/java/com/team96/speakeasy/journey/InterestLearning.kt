package com.team96.speakeasy.journey

import java.text.Normalizer
import java.util.Locale

/** DEC059: closed, bundled scenes; free-text interests never become generated prompts. */
enum class InterestTheme(val title:String,val preference:String) {
    NEUTRAL("Play together","play"), TRAINS("Train journey","trains"),
    ANIMALS("Animal trail","animals"), STORIES("Story pages","stories");
    companion object {
        fun fromInterest(value:String):InterestTheme = when(value.trim().lowercase(Locale.ROOT)) {
            "train","trains","ரயில்" -> TRAINS
            "animal","animals","விலங்குகள்" -> ANIMALS
            "story","stories","கதைகள்" -> STORIES
            else -> NEUTRAL
        }
    }
}

enum class PromptHelp(val caption:String) {
    GUIDED("Follow the picture"), CUE("Match the picture"), YOUR_TURN("Your turn")
}

/** ILR002/003: these are picture-task counters, never inferred speech/attention skills. */
data class PictureProgress(
    val choices:Int=0,val matches:Int=0,val noExtraHintMatches:Int=0,val helps:Int=0,
    val recentMatches:Int=0,val recentErrors:Int=0,val help:PromptHelp=PromptHelp.GUIDED,
    val lastDay:Long=0,
) {
    val optionCount:Int get()=if(help==PromptHelp.YOUR_TURN)3 else 2
    val needsBreak:Boolean get()=recentErrors>=2
    fun answer(correct:Boolean,day:Long):PictureProgress {
        val counted=if(choices<10000)1 else 0
        if(!correct)return copy(choices=choices+counted,recentMatches=0,recentErrors=(recentErrors+1).coerceAtMost(2),help=PromptHelp.GUIDED,lastDay=day.coerceIn(0,50000))
        val streak=recentMatches+1
        val next=if(streak>=2)PromptHelp.entries[(help.ordinal+1).coerceAtMost(2)]else help
        return copy(choices=choices+counted,matches=matches+counted,
            noExtraHintMatches=noExtraHintMatches+if(help==PromptHelp.YOUR_TURN)counted else 0,
            recentMatches=if(streak>=2)0 else streak,recentErrors=0,help=next,lastDay=day.coerceIn(0,50000))
    }
    fun requestedHelp(day:Long)=copy(helps=(helps+1).coerceAtMost(10000),recentMatches=0,recentErrors=0,help=PromptHelp.GUIDED,lastDay=day.coerceIn(0,50000))
    fun valid()=choices in 0..10000 && matches in 0..choices && noExtraHintMatches in 0..matches && helps in 0..10000 && recentMatches in 0..2 && recentErrors in 0..minOf(2,choices) && lastDay in 0..50000
}

data class PictureResponse(val progress:PictureProgress,val matched:Boolean)
data class SupportedPictureSelection(val response:PictureResponse,val withoutExtraHint:Boolean)
/** A requested example/help is support even when history loading or a failed write delays storage. */
fun pictureProgressWithSupport(progress:PictureProgress,extraSupportUsed:Boolean)=
    if(extraSupportUsed)progress.copy(help=PromptHelp.GUIDED,recentMatches=0)else progress
fun choosePictureWithSupport(target:String,selected:String,options:List<String>,progress:PictureProgress,day:Long,extraSupportUsed:Boolean):SupportedPictureSelection {
    val shown=pictureProgressWithSupport(progress,extraSupportUsed)
    return SupportedPictureSelection(pictureSelection(target,selected,options,shown,day),!extraSupportUsed && shown.help==PromptHelp.YOUR_TURN)
}
fun pictureSelection(target:String,selected:String,options:List<String>,progress:PictureProgress,day:Long):PictureResponse {
    val known=StarterWords.all.map{it.id}.toSet()
    require(options.size in 2..3 && options.distinct().size==options.size && options.all{it in known} && target in options && selected in options)
    require(WordActivityCatalog.isMatch(target) && options.all{it in WordActivityCatalog.pool(target)})
    return PictureResponse(progress.answer(target==selected,day),target==selected)
}

fun learningOptions(target:String,count:Int,turn:Int):List<String> {
    require(count in 2..3)
    val pool=WordActivityCatalog.pool(target)
    val others=pool.drop(1).take(count-1).toMutableList()
    val known=StarterWords.all.map{it.id}
    others.add(Math.floorMod(turn+known.indexOf(target),count),target)
    return others
}

/** ILR004: support/challenge is curricular picture load, not phoneme difficulty. */
fun adaptiveWordLessonId(current:Int,focused:Boolean,history:Map<String,PictureProgress>):Int? {
    val order=if(focused)StarterWords.focusedLessonIds else (1..StarterWords.all.size).toList()
    val index=order.indexOf(current);if(index<0)return null
    val remaining=order.drop(index+1);if(remaining.isEmpty())return null
    val record=StarterWords.byNumericLessonId(current)?.let{history[it.id]} ?: return remaining.first()
    val tier=when{record.recentErrors>0 -> 1;history.values.sumOf{it.noExtraHintMatches}>=4 -> 3;history.values.sumOf{it.noExtraHintMatches}>=2 -> 2;else -> 1}
    val window=remaining.take(4)
    if(record.recentErrors>0)return window.minBy{StarterWords.byNumericLessonId(it)!!.difficulty}
    val today=java.time.LocalDate.now().toEpochDay()
    val review=window.filter{lesson->
        val word=StarterWords.byNumericLessonId(lesson)!!;val past=history[word.id]
        past!=null && past.choices>0 && past.lastDay in 1 until today && word.difficulty<=tier
    }.minByOrNull{history[StarterWords.byNumericLessonId(it)!!.id]!!.lastDay}
    if(review!=null)return review
    return window.firstOrNull{StarterWords.byNumericLessonId(it)!!.difficulty<=tier} ?: remaining.first()
}

/** ILR005: orthographic blocks only. No heuristic syllables, fragment TTS or sound-error labels. */
fun tamilWritingParts(value:String):List<String> {
    val word=Normalizer.normalize(value,Normalizer.Form.NFC);if(word.isBlank())return emptyList()
    val parts=mutableListOf<String>()
    for(char in word){
        if(char.code !in 0x0B80..0x0BFF)return emptyList()
        val kind=Character.getType(char)
        if(kind==Character.NON_SPACING_MARK.toInt() || kind==Character.COMBINING_SPACING_MARK.toInt()){
            if(parts.isEmpty())return emptyList()
            parts[parts.lastIndex]=parts.last()+char
        }else if(Character.isLetter(char))parts.add(char.toString())else return emptyList()
    }
    return parts
}

object WordLearningPacing {
    /** DEC070: ROUND is a brief cycle boundary; never restart the accumulated attention window. */
    fun continueAutonomousRound(clock:LetterSession,settlingMs:Long):LetterSession {
        if(clock.reason!=LetterPause.ROUND)return clock
        if(clock.totalActiveMs>=clock.sessionMs)return clock.copy(reason=LetterPause.END)
        if(clock.blockActiveMs>=clock.focusMs)return clock.copy(reason=LetterPause.FOCUS)
        return clock.copy(roundPractised=0,reason=LetterPause.NONE).tick(settlingMs.coerceAtLeast(0))
    }
    fun start(plan:CarePlan):LetterSession {
        val safe=normalizeCarePlan(plan)
        return LetterSession.start(3,safe.focusMinutes*60000L,safe.sessionMinutes*60000L)
    }
    fun restore(values:List<Long>)=LetterSession.restore(values).pause(LetterPause.BACKGROUND)
    fun resume(clock:LetterSession):LetterSession =
        if(clock.reason==LetterPause.BACKGROUND && clock.roundPractised<clock.roundSize && clock.blockActiveMs<clock.focusMs)clock.copy(reason=LetterPause.NONE)else clock.resume()
}

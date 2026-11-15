package com.team96.speakeasy.audio

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import android.os.Handler
import android.os.Looper
import com.team96.speakeasy.journey.LocalPromptLibrary
import java.util.UUID
import android.os.Bundle
import com.team96.speakeasy.journey.PraiseStyle
import com.team96.speakeasy.journey.PraiseEvent
import com.team96.speakeasy.journey.praiseLine

enum class SpeechReadiness{PREPARING,READY,UNAVAILABLE}

/** DEC025/056 review R4: explicitly selected installed offline Tamil voice, with no fallback. */
class LocalTamilSpeaker(
    context:Context,private val onUnavailable:()->Unit={},onSpeaking:(Boolean)->Unit,
):TextToSpeech.OnInitListener {
    private val main=Handler(Looper.getMainLooper())
    private val playback=VoicePlaybackGuard(onSpeaking,onUnavailable)
    private val speakerId=UUID.randomUUID().toString()
    private var selected:OfflineVoiceCandidate?=null
    private var ready=false
    private var closed=false
    private var initialized=false
    val readiness:SpeechReadiness get()=when{closed->SpeechReadiness.UNAVAILABLE;!initialized->SpeechReadiness.PREPARING;ready->SpeechReadiness.READY;else->SpeechReadiness.UNAVAILABLE}
    private val tts=TextToSpeech(context.applicationContext,this)
    private fun Voice.candidate()=OfflineVoiceCandidate(name,locale.language,isNetworkConnectionRequired,
        features.orEmpty().contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED))

    override fun onInit(status:Int){main.post{
        initialized=true
        if(closed || status!=TextToSpeech.SUCCESS)return@post
        val voices=runCatching{tts.voices.orEmpty().toList()}.getOrDefault(emptyList())
        val candidate=chooseOfflineTamilVoice(voices.map{it.candidate()}) ?: return@post
        val voice=voices.first{it.name==candidate.name}
        val accepted=runCatching{tts.setVoice(voice)==TextToSpeech.SUCCESS}.getOrDefault(false)
        val active=runCatching{tts.voice?.candidate()}.getOrNull()
        ready=isSelectedOfflineTamilVoice(candidate,accepted,active)
        if(!ready)return@post
        selected=candidate
        tts.setOnUtteranceProgressListener(object:UtteranceProgressListener(){
            override fun onStart(utteranceId:String?){main.post{playback.started(utteranceId)}}
            override fun onDone(utteranceId:String?){main.post{utteranceId?.let{owners.finished(speakerId,it)};playback.finished(utteranceId)}}
            @Deprecated("Deprecated in Java") override fun onError(utteranceId:String?){main.post{utteranceId?.let{owners.finished(speakerId,it)};playback.failed(utteranceId)}}
            override fun onError(utteranceId:String?,errorCode:Int){main.post{utteranceId?.let{owners.finished(speakerId,it)};playback.failed(utteranceId)}}
            override fun onStop(utteranceId:String?,interrupted:Boolean){main.post{utteranceId?.let{owners.finished(speakerId,it)};playback.finished(utteranceId)}}
        })
    }}
    fun speakWord(target:String):Boolean = LocalPromptLibrary.wordExample(target)?.let{ speakApproved(it) } ?: false
    fun speakLetter(id:String):Boolean = LocalPromptLibrary.letterExample(id)?.let{ speakApproved(it) } ?: false
    /** DEC069/PHN010: only closed authored exploration steps; no generated child prompt. */
    fun speakSoundStep(recipe:SoundRecipe,step:Int,wordId:String):Boolean =
        SoundPracticeCatalog.steps(recipe,wordId).getOrNull(step)?.let{speakApproved(it)}?:false
    /** COA001: only closed neutral prompts; no arbitrary LLM-generated child-facing text. */
    fun speakCoach(cue:PracticeCoachCue):Boolean = speakApproved(cue.tamil,rate=.9f,volume=.85f)
    /** PRS001/004: original local praise; stock system voice, never a celebrity voice/reference. */
    fun speakPraise(alias:String,style:PraiseStyle,event:PraiseEvent):Boolean =
        speakApproved(praiseLine(alias,style,event),style.rate,style.pitch,.60f,SpeechKind.PRAISE)
    private fun speakApproved(text:String,rate:Float=1f,pitch:Float=1f,volume:Float=1f,kind:SpeechKind=SpeechKind.EXAMPLE):Boolean {
        val voice=selected ?: return false
        if(closed || !ready || !isSelectedOfflineTamilVoice(voice,true,runCatching{tts.voice?.candidate()}.getOrNull()))return false
        // Reset every utterance, so a cheer cannot change the next teaching example's delivery.
        if(tts.setSpeechRate(rate)!=TextToSpeech.SUCCESS || tts.setPitch(pitch)!=TextToSpeech.SUCCESS)return false
        val params=Bundle().apply{putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME,volume)}
        val id=UUID.randomUUID().toString()
        owners.begin(speakerId,id,kind)
        playback.begin(id)
        val accepted=runCatching{tts.speak(text,TextToSpeech.QUEUE_FLUSH,params,id)==TextToSpeech.SUCCESS}.getOrDefault(false)
        if(!accepted){owners.finished(speakerId,id);playback.failed(id)}
        return accepted
    }
    fun stopPraise(){if(owners.stop(speakerId,SpeechKind.PRAISE)){playback.stop();tts.stop()}}
    fun stop(){val own=owners.stop(speakerId);playback.stop();if(own)tts.stop()}
    fun shutdown(){closed=true;ready=false;stop();tts.shutdown()}
    companion object{private val owners=SpeechOwnership()}
}

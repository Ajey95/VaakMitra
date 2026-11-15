package com.team96.speakeasy.audio

/** DEC025/056 review R4: no downloadable or network fallback can satisfy this voice gate. */
data class OfflineVoiceCandidate(val name:String,val language:String,val networkRequired:Boolean,val notInstalled:Boolean)
fun chooseOfflineTamilVoice(voices:List<OfflineVoiceCandidate>):OfflineVoiceCandidate? =
    voices.firstOrNull{it.language.equals("ta",true) && !it.networkRequired && !it.notInstalled}
fun isSelectedOfflineTamilVoice(expected:OfflineVoiceCandidate,selected:Boolean,active:OfflineVoiceCandidate?):Boolean =
    selected && active==expected && chooseOfflineTamilVoice(listOf(expected))!=null

/** Late callbacks from a stopped example cannot affect the next letter. */
class VoicePlaybackGuard(private val onSpeaking:(Boolean)->Unit,private val onUnavailable:()->Unit){
    private var active:String?=null
    @Synchronized fun begin(id:String){active=id}
    @Synchronized fun started(id:String?){if(id!=null && id==active)onSpeaking(true)}
    @Synchronized fun finished(id:String?){if(id!=null && id==active){active=null;onSpeaking(false)}}
    @Synchronized fun failed(id:String?){if(id!=null && id==active){active=null;onSpeaking(false);onUnavailable()}}
    @Synchronized fun stop(){active=null;onSpeaking(false)}
}

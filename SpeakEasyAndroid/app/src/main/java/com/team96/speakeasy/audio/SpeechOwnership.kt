package com.team96.speakeasy.audio

enum class SpeechKind{EXAMPLE,PRAISE}
/** DEC064: departing praise cannot stop teaching or another speaker. */
class SpeechOwnership {
 private data class Lease(val speaker:String,val utterance:String,val kind:SpeechKind)
 private var current:Lease?=null
 @Synchronized fun begin(speaker:String,utterance:String,kind:SpeechKind){current=Lease(speaker,utterance,kind)}
 @Synchronized fun owns(speaker:String,utterance:String)=current?.let{it.speaker==speaker&&it.utterance==utterance}?:false
 @Synchronized fun finished(speaker:String,utterance:String){if(owns(speaker,utterance))current=null}
 @Synchronized fun stop(speaker:String,kind:SpeechKind?=null):Boolean {
  val active=current?:return false
  if(active.speaker!=speaker||(kind!=null&&active.kind!=kind))return false
  current=null;return true
 }
}

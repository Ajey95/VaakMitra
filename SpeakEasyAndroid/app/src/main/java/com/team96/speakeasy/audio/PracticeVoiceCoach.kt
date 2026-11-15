package com.team96.speakeasy.audio

import com.team96.speakeasy.journey.StarterWords

private val coachStatuses=setOf("diagnostic_only","insufficient_evidence","unsupported_reference","invalid_evidence","ambiguous_alignment","sequence_agreement")
private val coachConditions=setOf("low_recording_level","clipped_recording","unclear_recording","long_attempt","pause_variation")
private val coachHypotheses=setOf("possible_substitution","possible_omission")
private val coachAllowed=listOf("demonstrate_target","offer_sound_practice","ask_rerecord","offer_break")
private val coachForbidden=listOf("claim_child_error","diagnose","score","force_retry")

/** COA001: original closed Tamil coaching, no inferred defect or generated TTS text. */
enum class PracticeCoachCue(val caption:String,val tamil:String) {
    QUIET("I couldn't hear clearly. You can bring the phone a little closer.","எனக்குத் தெளிவாகக் கேட்கவில்லை. கைபேசியைச் சற்றே அருகில் வைத்து, வசதியாகச் சொல்லலாம்."),
    CLIPPED("The recording wasn't clear. Let's try with the phone a little farther away.","சத்தம் தெளிவாகப் பதிவாகவில்லை. கைபேசியைச் சற்றே தள்ளி வைத்துப் பார்க்கலாம்."),
    OWN_PACE("Take your time. Let's listen to one small part together.","அவசரம் இல்லை. உன் வேகத்தில் சொல்லலாம். முதலில் இந்தச் சிறிய பகுதியைக் கேட்கலாம்."),
    UNCLEAR("Let's listen together. You can try when you're ready.","பரவாயில்லை. ஒன்றாகக் கேட்டுப் பழகலாம். தயாரானதும் சொல்லலாம்."),
    SOUND_EXAMPLE("Let's listen to this sound together.","இந்த ஒலியை ஒன்றாகக் கேட்டு, பிறகு சொல்லலாம்."),
    TOGETHER("Thanks for trying. Let's listen to the word together.","நன்றாக முயற்சி செய்தாய். இந்தச் சொல்லை ஒன்றாகக் கேட்கலாம்."),
}

/** Minimal allow-listed semantic text only; never recordings, waveforms or voice features. */
data class CoachSoundDifference(val expectedSound:String,val hypothesis:String,val confirmed:Boolean=false) {
    init{require(SoundPracticeCatalog.find(expectedSound)!=null && hypothesis in coachHypotheses && !confirmed)}
}
data class CoachToolResult(
    val targetWordId:String,val evidenceStatus:String,val recordingCondition:String?,
    val possibleDifferences:List<CoachSoundDifference>,val localOnly:Boolean=true,
    val allowedActions:List<String> = coachAllowed,
    val forbiddenActions:List<String> = coachForbidden,
) {
    init {
        require(StarterWords.all.any{it.id==targetWordId} && evidenceStatus in coachStatuses)
        require(recordingCondition==null || recordingCondition in coachConditions)
        require(localOnly && allowedActions==coachAllowed && forbiddenActions==coachForbidden)
        require(evidenceStatus=="diagnostic_only" || possibleDifferences.isEmpty())
    }
    fun toToolFields():Map<String,Any?> = mapOf(
        "schema" to "vaakmitra.speech_analysis.v1","target_word_id" to targetWordId,
        "evidence_status" to evidenceStatus,"recording_conditions" to listOfNotNull(recordingCondition),
        "possible_sound_differences" to possibleDifferences.map{mapOf("expected_sound" to it.expectedSound,"hypothesis" to it.hypothesis,"confirmed" to false)},
        "child_correctness" to null,"clinical_assessment" to false,"local_only" to true,
        "allowed_actions" to allowedActions,"forbidden_actions" to forbiddenActions,
    )
}

object PracticeVoiceCoach {
    fun needsFullGuide(cue:PracticeCoachCue?)=cue!=null && cue!=PracticeCoachCue.TOGETHER
    fun choose(outcome:LocalWordOutcome,capture:PcmCaptureEvidence?=null):PracticeCoachCue? = when(outcome.reason){
        "MODEL_UNAVAILABLE","TARGET_UNAVAILABLE","UNSUPPORTED_SAMPLE_RATE","INFERENCE_ERROR"->null
        "CLIPPED"->PracticeCoachCue.CLIPPED
        "TOO_LONG"->PracticeCoachCue.OWN_PACE
        "NO_SPEECH","VAD_NO_SPEECH","TOO_SHORT"->
            if(capture!=null && capture.sampleCount>0 && capture.rms<80 && capture.peakAbsolute<1024)PracticeCoachCue.QUIET else PracticeCoachCue.UNCLEAR
        "PHONEME_EMPTY"->PracticeCoachCue.UNCLEAR
        // COA002: the adult contrast gate failed; alignment cannot select a sound cue.
        "PHONEME_TOKENS"->PracticeCoachCue.TOGETHER
        else->null
    }
    /** COA002: retain the guide interface while unqualified sound localization stays research-only. */
    @Suppress("UNUSED_PARAMETER")
    fun focusSound(alignment:PauseAlignmentResult?,reference:List<String>):SoundRecipe? = null
    fun toolResult(wordId:String,alignment:PauseAlignmentResult?,cue:PracticeCoachCue?):CoachToolResult {
        require(StarterWords.all.any{it.id==wordId})
        val candidates=emptyList<CoachSoundDifference>()
        val condition=when(cue){PracticeCoachCue.QUIET->"low_recording_level";PracticeCoachCue.CLIPPED->"clipped_recording";
            PracticeCoachCue.OWN_PACE->"long_attempt";PracticeCoachCue.UNCLEAR->"unclear_recording";else->null}
        val status=alignment?.status?.takeIf{it in coachStatuses && it!="diagnostic_only"}?:"insufficient_evidence"
        return CoachToolResult(wordId,status,condition,candidates)
    }
}

/** Existing cue lease owns playback; a preface never records or bypasses cancellation. */
suspend fun runCoachPreface(
    cadence:GuideCadence=GuideCadence(visualMs=1200,imitationMs=300,voiceFinishMs=8000),
    allowed:()->Boolean,play:()->Boolean,isSpeaking:()->Boolean,stop:()->Unit,
):Boolean=runGuideCues(listOf(0),cadence,allowed,{}, {play()},isSpeaking,stop)

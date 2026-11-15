package com.team96.speakeasy.journey

/** DEC053 review R3: never reread dirty preference memory as a successful durable write. */
class ConfirmedLetterWrites(initial:LetterJourneySnapshot,private val persist:(LetterJourneySnapshot)->Boolean){
    private var confirmed=initial
    @Synchronized fun load():LetterJourneySnapshot=confirmed
    @Synchronized fun complete(id:String):LetterJourneySnapshot {
        val next=confirmed.progress.complete(id)
        if(next==confirmed.progress)return confirmed
        return save(confirmed.copy(progress=next))
    }
    @Synchronized fun saveSettings(settings:LetterPracticeSettings):LetterJourneySnapshot =
        save(confirmed.copy(settings=LetterPracticeSettings.normalize(settings.roundSize,settings.rewardsEnabled)))
    private fun save(candidate:LetterJourneySnapshot):LetterJourneySnapshot {
        check(persist(candidate)){"letter_progress_not_saved"}
        confirmed=candidate
        return confirmed
    }
}

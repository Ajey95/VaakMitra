package com.team96.speakeasy.journey

import android.content.Context

/** DEC053/PRV001 review R3: scoped counts/settings only, with last-confirmed write ownership. */
class LetterJourneyStore(context:Context,val scope:String){
    private val preferences=context.applicationContext.getSharedPreferences("vaakmitra_letter_journey_v1",Context.MODE_PRIVATE)
    init{require(scope.matches(Regex("[a-f0-9]{32}")))}
    private val cacheKey=context.applicationContext.filesDir.absolutePath+":"+scope
    private val writer:ConfirmedLetterWrites get()=writers.getOrPut(cacheKey){
        val initial=try{
            LetterJourneySnapshot(
                LetterProgress.restore(preferences.getInt("${scope}_completed",0),preferences.getInt("${scope}_version",1)),
                LetterPracticeSettings.normalize(preferences.getInt("${scope}_round",3),preferences.getBoolean("${scope}_rewards",true)),
            )
        }catch(_:ClassCastException){LetterJourneySnapshot()}
        ConfirmedLetterWrites(initial){candidate->
            preferences.edit().putInt("${scope}_version",1).putInt("${scope}_completed",candidate.progress.completedCount)
                .putInt("${scope}_round",candidate.settings.roundSize).putBoolean("${scope}_rewards",candidate.settings.rewardsEnabled).commit()
        }
    }
    fun load():LetterJourneySnapshot=synchronized(lock){writer.load()}
    fun complete(id:String):LetterJourneySnapshot=synchronized(lock){writer.complete(id)}
    fun saveSettings(settings:LetterPracticeSettings):LetterJourneySnapshot=synchronized(lock){writer.saveSettings(settings)}
    companion object{
        private val lock=Any()
        // Shared across store instances: a failed commit's dirty preference map is never reloaded.
        private val writers=mutableMapOf<String,ConfirmedLetterWrites>()
    }
}

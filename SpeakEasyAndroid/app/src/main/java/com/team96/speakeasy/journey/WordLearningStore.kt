package com.team96.speakeasy.journey

import android.content.Context

/** ILR007: separate verified child/account namespace; public previews never instantiate this. */
class WordLearningStore(context:Context,val scope:String,private val stillOwner:()->Boolean) {
    private val preferences=context.applicationContext.getSharedPreferences("vaakmitra_word_learning_v2",Context.MODE_PRIVATE)
    private val cacheKey=context.applicationContext.filesDir.absolutePath+":v2:"+scope
    init{require(scope.matches(Regex("[a-f0-9]{32}")))}
    private val writer:ConfirmedWordLearningWrites get()=writers.getOrPut(cacheKey){
        val initial=runCatching{WordProgressCodec.decode(preferences.getString("${scope}_records","").orEmpty())}.getOrDefault(emptyMap())
        ConfirmedWordLearningWrites(initial,{next->preferences.edit().putString("${scope}_records",WordProgressCodec.encode(next)).commit()},stillOwner)
    }
    fun load():Map<String,PictureProgress> =synchronized(lock){writer.load()}
    fun choose(id:String,selected:String,options:List<String>,day:Long):Boolean=synchronized(lock){writer.choose(id,selected,options,day)}
    fun help(id:String,day:Long):Boolean=synchronized(lock){writer.help(id,day)}
    fun put(id:String,progress:PictureProgress):Boolean=synchronized(lock){writer.put(id,progress)}
    companion object{
        private val lock=Any()
        private val writers=mutableMapOf<String,ConfirmedWordLearningWrites>()
    }
}

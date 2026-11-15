package com.team96.speakeasy.audio

import com.team96.speakeasy.journey.StarterWords

/** DEC069/PHN010: transient exploration opportunities, not a child's error or confidence score. */
data class SoundPracticeEvidence(val wordId:String,val possibleSounds:Set<String>,val sequenceAgrees:Boolean=false)
data class SoundRecipe(val token:String,val sound:String,val syllable:String)

object SoundPracticeCatalog {
    // Closed authored examples. System-voice delivery remains explicitly unverified.
    val all=listOf(
        SoundRecipe("m","ம்","மா"),SoundRecipe("p","ப்","பா"),SoundRecipe("k","க்","கா"),
        SoundRecipe("ʋ","வ்","வா"),SoundRecipe("t̪","த்","தா"),SoundRecipe("ʈ","ட்","டா"),
        SoundRecipe("l","ல்","லா"),SoundRecipe("n","ன்","னா"),SoundRecipe("n̪","ந்","நா"),SoundRecipe("ɳ","ண்","ணா"),
        SoundRecipe("a","அ","ம"),SoundRecipe("aː","ஆ","மா"),SoundRecipe("i","இ","மி"),SoundRecipe("iː","ஈ","மீ"),
        SoundRecipe("u","உ","மு"),SoundRecipe("uː","ஊ","மூ"),SoundRecipe("e","எ","மெ"),SoundRecipe("eː","ஏ","மே"),
        SoundRecipe("o","ஒ","மொ"),SoundRecipe("oː","ஓ","மோ"),
    )
    fun find(token:String)=all.firstOrNull{it.token==token}
    fun forWord(reference:List<String>)=all.firstOrNull{it.token in reference}
    fun steps(recipe:SoundRecipe,wordId:String):List<String> {
        if(find(recipe.token)!=recipe)return emptyList()
        val word=StarterWords.all.firstOrNull{it.id==wordId}?:return emptyList()
        return listOf(recipe.sound,recipe.syllable,word.tamil)
    }
}

object SoundPracticePolicy {
    private data class Cell(val cost:Int,val targets:Set<String>,val insertion:Boolean=false)
    private fun extend(cell:Cell,phone:String?=null,insertion:Boolean=false)=
        Cell(cell.cost+if(phone!=null || insertion)1 else 0,cell.targets+listOfNotNull(phone),cell.insertion||insertion)
    private fun align(heard:List<String>,reference:List<String>):Cell {
        var previous=List(reference.size+1){j->Cell(j,reference.take(j).toSet())}
        for(phone in heard){
            val row=mutableListOf(extend(previous.first(),insertion=true))
            for((index,target)in reference.withIndex()){
                val options=listOf(extend(previous[index+1],insertion=true),extend(row[index],target),
                    extend(previous[index],if(phone==target)null else target))
                val best=options.minOf{it.cost};val tied=options.filter{it.cost==best}
                row.add(Cell(best,tied.flatMap{it.targets}.toSet(),tied.any{it.insertion}))
            }
            previous=row
        }
        return previous.last()
    }
    fun evidence(wordId:String,heard:List<String>,reference:List<String>,known:Set<String>):SoundPracticeEvidence? {
        if(StarterWords.all.none{it.id==wordId})return null
        fun valid(phones:List<String>)=phones.size in 1..64 && phones.all{it in known && it !in setOf("<blank>","[UNK]","[PAD]","|")}
        if(!valid(heard)||!valid(reference))return null
        val variants=mutableListOf(reference)
        // Whole-word variants only: never change the recognizer or normalize arbitrary c/s pairs.
        if(wordId in setOf("TA_WORD_0049","TA_WORD_0100") && reference.first()=="t͡ʃ")variants.add(listOf("s")+reference.drop(1))
        if(heard in variants)return SoundPracticeEvidence(wordId,emptySet(),sequenceAgrees=true)
        val outcomes=variants.map{align(heard,it)};val cost=outcomes.minOf{it.cost};val best=outcomes.filter{it.cost==cost}
        val targets=best.flatMap{it.targets}.toSet()
        if(cost>2 || cost*2>reference.size || best.any{it.insertion} || targets.size!=1)return null
        if(SoundPracticeCatalog.find(targets.single())==null)return null
        return SoundPracticeEvidence(wordId,targets)
    }
    fun relatedLesson(current:Int,focused:Boolean,wordIds:Set<String>):Int? {
        val itinerary=if(focused)StarterWords.focusedLessonIds else (1..StarterWords.all.size).toList()
        val index=itinerary.indexOf(current);if(index<0)return null
        val currentWord=StarterWords.byNumericLessonId(current)?:return null
        return itinerary.drop(index+1).firstOrNull{lesson->StarterWords.byNumericLessonId(lesson)?.let{
            it.id in wordIds && it.difficulty<=currentWord.difficulty
        }==true}
    }
}

/** Session memory only. No Saver, file, report field, raw sequence or inferred diagnostic label. */
class SoundPracticeTracker {
    private val observations=ArrayDeque<SoundPracticeEvidence?>()
    fun record(evidence:SoundPracticeEvidence?) {
        val valid=evidence?.takeIf{row->StarterWords.all.any{it.id==row.wordId}}
        if(valid?.sequenceAgrees==true){
            val cleared=observations.map{if(it?.wordId==valid.wordId)null else it}
            observations.clear();observations.addAll(cleared)
        }
        val candidate=valid?.takeIf{!it.sequenceAgrees && it.possibleSounds.size==1 && SoundPracticeCatalog.find(it.possibleSounds.single())!=null}
        // Every attempt ages the window, including unusable and agreeing observations.
        observations.addLast(candidate)
        while(observations.size>24)observations.removeFirst()
    }
    fun prioritizedSound(allowed:Set<String> = SoundPracticeCatalog.all.map{it.token}.toSet()):SoundRecipe? =
        SoundPracticeCatalog.all.filter{recipe->recipe.token in allowed && observations.filterNotNull().filter{recipe.token in it.possibleSounds}.let{
            it.size>=3 && it.map{it.wordId}.distinct().size>=2
        }}.maxByOrNull{recipe->observations.count{it!=null && recipe.token in it.possibleSounds}}
    fun clear(){observations.clear()}
}

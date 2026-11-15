package com.team96.speakeasy.journey

/** DEC061: authored examples, never inferred diagnoses or the learner's actual family. */
enum class WordArt { MOTHER,FATHER,FOOD,HEAD,HAND,HOME,REQUEST,DECLINE,MORE,ENOUGH,HELP,SPEAK,READ,PICTURE,NO,YES,SAFETY,AGAIN,HERE,THERE,TOGETHER,WHAT,SELF,THIS,FOR_ME }
data class ContextExample(val art:WordArt,val prompt:String,val before:String,val after:String)

object WordActivityCatalog {
    val matchIds=setOf("TA_WORD_0001","TA_WORD_0002","TA_WORD_0012","TA_WORD_0086","TA_WORD_0084","TA_WORD_0061")
    private val concrete=mapOf(
        "TA_WORD_0001" to WordArt.MOTHER,"TA_WORD_0002" to WordArt.FATHER,
        "TA_WORD_0012" to WordArt.FOOD,"TA_WORD_0086" to WordArt.HEAD,
        "TA_WORD_0084" to WordArt.HAND,"TA_WORD_0061" to WordArt.HOME,
    )
    private val examples=mapOf(
        "TA_WORD_0013" to ContextExample(WordArt.REQUEST,"Ask for the ball","The child would like the ball","Ball offered to the child"),
        "TA_WORD_0014" to ContextExample(WordArt.DECLINE,"Decline an offered ball","A ball is offered","The child chooses not to take it"),
        "TA_WORD_0015" to ContextExample(WordArt.MORE,"Ask for another block","Two blocks to build with","One more block joins the tower"),
        "TA_WORD_0016" to ContextExample(WordArt.ENOUGH,"Finish the play turn","The toys are out","Toys put away for a break"),
        "TA_WORD_0017" to ContextExample(WordArt.HELP,"Ask for help opening the toy box","The toy box is closed","A grown-up helps open the box"),
        "TA_WORD_0049" to ContextExample(WordArt.SPEAK,"Say a word with a partner","Two people are ready to listen","A turn to say a word"),
        "TA_WORD_0050" to ContextExample(WordArt.READ,"Read a book together","A book is closed","An open book to read together"),
        "TA_WORD_0072" to ContextExample(WordArt.PICTURE,"Look at the framed picture","A picture in its frame","The child points to the picture"),
        "TA_WORD_0082" to ContextExample(WordArt.NO,"Say no to an offered ball","A ball is offered","A calm no; the ball stays away"),
        "TA_WORD_0083" to ContextExample(WordArt.YES,"Say yes to an offered ball","A ball is offered","The child accepts the ball"),
        "TA_WORD_0090" to ContextExample(WordArt.SAFETY,"Stay together by the crossing","A grown-up and child at the path","Holding hands beside the crossing"),
        "TA_WORD_0096" to ContextExample(WordArt.AGAIN,"Roll the ball again","A ball ready to roll","Another turn rolling the ball"),
        "TA_WORD_0098" to ContextExample(WordArt.HERE,"Point to the mat beside the child","A mat near the child","Here: the mat beside the child"),
        "TA_WORD_0099" to ContextExample(WordArt.THERE,"Point to the mat away from the child","A mat farther from the child","There: the mat away from the child"),
        "TA_WORD_0100" to ContextExample(WordArt.TOGETHER,"Play side by side","Two children with a ball","A shared turn together"),
        "TA_WORD_0101" to ContextExample(WordArt.WHAT,"Ask what is inside the box","A box with something inside","Look: a ball inside the box"),
        "TA_WORD_0102" to ContextExample(WordArt.SELF,"The child points to themself","Meet the child in this example","I / me: the child points to themself"),
        "TA_WORD_0103" to ContextExample(WordArt.THIS,"Point to this ball","A ball beside the child","This: the ball being pointed to"),
        "TA_WORD_0104" to ContextExample(WordArt.FOR_ME,"Pass the ball to the child","A ball ready to share","For me: the ball goes to the child"),
    )
    fun isMatch(id:String)=id in matchIds
    fun art(id:String):WordArt=concrete[id] ?: examples[id]?.art ?: throw IllegalArgumentException("Unknown activity ID")
    fun context(id:String):ContextExample? {art(id);return examples[id]}
    fun pictureCaption(id:String):String=when(art(id)){
        WordArt.MOTHER->"Mother with child";WordArt.FATHER->"Father with child"
        WordArt.FOOD->"A meal on a leaf";WordArt.HEAD->"Head";WordArt.HAND->"Hand";WordArt.HOME->"A home"
        else->throw IllegalArgumentException("Context examples are not picture answers")
    }
    fun pool(id:String):List<String> =when(id){
        "TA_WORD_0001"->listOf(id,"TA_WORD_0002","TA_WORD_0061")
        "TA_WORD_0002"->listOf(id,"TA_WORD_0001","TA_WORD_0061")
        "TA_WORD_0012"->listOf(id,"TA_WORD_0061","TA_WORD_0084")
        "TA_WORD_0086"->listOf(id,"TA_WORD_0084","TA_WORD_0061")
        "TA_WORD_0084"->listOf(id,"TA_WORD_0086","TA_WORD_0012")
        "TA_WORD_0061"->listOf(id,"TA_WORD_0012","TA_WORD_0084")
        else->throw IllegalArgumentException("No matching task for this word")
    }
}

/** A scene illustrates this round's turn count, not a repeating reward or speech score. */
fun playSceneStep(turns:Int)=turns.coerceIn(0,3)
fun PictureProgress.validFor(id:String)=valid() && StarterWords.all.any{it.id==id} &&
    (WordActivityCatalog.isMatch(id) || (choices==0 && matches==0 && noExtraHintMatches==0 && recentMatches==0 && recentErrors==0 && help==PromptHelp.GUIDED))
fun InterestTheme.choiceLabel()=when(this){InterestTheme.TRAINS->"Train";InterestTheme.ANIMALS->"Animals";InterestTheme.STORIES->"Storybook";InterestTheme.NEUTRAL->"Play"}
fun InterestTheme.tamilLabel()=when(this){InterestTheme.TRAINS->"ரயில்";InterestTheme.ANIMALS->"விலங்குகள்";InterestTheme.STORIES->"கதைப்புத்தகம்";InterestTheme.NEUTRAL->"விளையாட்டு"}
fun wordIdlePrompt(id:String,explored:Boolean):String {
    WordActivityCatalog.art(id)
    return if(WordActivityCatalog.isMatch(id))"Choose a picture. Speaking is optional."
    else if(explored)"Tap See it again. Speaking is optional." else "Tap Show the action. Speaking is optional."
}

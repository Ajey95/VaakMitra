package com.team96.speakeasy.audio

import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.exp

/** PHN012/PRV001: owned frame evidence is consumed locally and explicitly erased. */
class OwnedPosteriorEvidence private constructor(val probabilities:Array<FloatArray>,val tokens:List<String>):AutoCloseable {
    override fun close(){probabilities.forEach{it.fill(0f)}}
    companion object {
        fun fromLogits(logits:Array<FloatArray>,tokens:List<String>):OwnedPosteriorEvidence {
            require(tokens.isNotEmpty() && tokens.distinct().size==tokens.size && logits.size in 1..400 && logits.all{it.size==tokens.size && it.all{v->v.isFinite()}})
            val probabilities=Array(logits.size){i->
                val maximum=logits[i].maxOrNull()!!
                val total=logits[i].sumOf{exp((it-maximum).toDouble())}
                FloatArray(tokens.size){j->(exp((logits[i][j]-maximum).toDouble())/total).toFloat()}
            }
            return OwnedPosteriorEvidence(probabilities,tokens.toList())
        }
    }
}

/** PHN012: transient model-support hypotheses, never a child correctness decision. */
data class AlignedPhone(
    val expected:String,val observed:String?,val kind:String,
    val startFrame:Int?=null,val endFrame:Int?=null,val confirmed:Boolean=false,
)
data class PauseAlignmentResult(val status:String,val phones:List<AlignedPhone> = emptyList())

object PauseAwareAlignment {
    private data class Span(val token:String,val start:Int,val end:Int,val mean:DoubleArray,val strong:Boolean)
    fun align(probabilities:Array<FloatArray>,tokens:List<String>,reference:List<String>):PauseAlignmentResult {
        if(probabilities.size !in 1..400 || tokens.isEmpty() || tokens.first()!="<blank>" || tokens.distinct().size!=tokens.size ||
            probabilities.any{row->row.size!=tokens.size || row.any{!it.isFinite() || it<0f || it>1f} || abs(row.sum().toDouble()-1)>1e-4})
            return PauseAlignmentResult("invalid_evidence")
        val known=tokens.toSet()-setOf("<blank>","|","[UNK]","[PAD]","்")
        if(reference.isEmpty() || reference.size>64 || reference.any{it !in known})return PauseAlignmentResult("unsupported_reference")
        val ids=tokens.withIndex().associate{it.value to it.index}
        val maxima=IntArray(probabilities.size){i->probabilities[i].indices.maxBy{probabilities[i][it]}}
        val spans=mutableListOf<Span>();var index=0
        var scratchCosts:Array<DoubleArray>?=null
        var scratchActions:Array<IntArray>?=null
        try {
            while(index<probabilities.size){
                val start=index;val chosen=maxima[index];index++
                while(index<probabilities.size && maxima[index]==chosen)index++
                if(tokens[chosen] in setOf("<blank>","|"))continue
                // Native compounds expand after decoding. Do not invent per-component
                // acoustic support when their individual boundaries are unresolved.
                if(tokens[chosen] in setOf("aj","aʋ","kʂ"))return PauseAlignmentResult("insufficient_evidence")
                val mean=DoubleArray(tokens.size){j->(start until index).sumOf{probabilities[it][j].toDouble()}/(index-start)}
                val competitor=mean.indices.filter{it!=chosen}.maxOfOrNull{mean[it]}?:0.0
                spans.add(Span(tokens[chosen],start,index,mean,mean[chosen]>=.65 && mean[chosen]-competitor>=.2))
            }
            if(spans.isEmpty() || spans.any{it.token !in known} || spans.none{it.strong})return PauseAlignmentResult("insufficient_evidence")
            val n=reference.size;val m=spans.size
            val costs=Array(n+1){DoubleArray(m+1){Double.POSITIVE_INFINITY}};costs[0][0]=0.0;scratchCosts=costs
            val actions=Array(n+1){IntArray(m+1)};scratchActions=actions
            val paths=Array(n+1){IntArray(m+1)};paths[0][0]=1
            for(a in 0..n)for(b in 0..m){
                if(a==0 && b==0)continue
                val options=mutableListOf<Triple<Double,Int,Int>>()
                if(a>0 && b>0){
                    val probability=spans[b-1].mean[ids.getValue(reference[a-1])]
                    options.add(Triple(costs[a-1][b-1]+minOf(2.0,-ln(probability.coerceAtLeast(1e-9))/3),1,paths[a-1][b-1]))
                }
                if(a>0)options.add(Triple(costs[a-1][b]+1.5,2,paths[a-1][b]))
                if(b>0)options.add(Triple(costs[a][b-1]+1.5,3,paths[a][b-1]))
                val best=options.minBy{it.first};costs[a][b]=best.first;actions[a][b]=best.second
                paths[a][b]=options.filter{abs(it.first-best.first)<=1e-8}.sumOf{it.third}.coerceAtMost(2)
            }
            if(paths[n][m]>1)return PauseAlignmentResult("ambiguous_alignment")
            var a=n;var b=m;val result=mutableListOf<AlignedPhone>()
            while(a>0 || b>0){when(actions[a][b]){
                1->{val span=spans[b-1];val expected=reference[a-1]
                    val kind=if(!span.strong)"uncertain" else if(span.token==expected)"model_support" else "possible_substitution"
                    result.add(AlignedPhone(expected,span.token,kind,span.start,span.end));a--;b--}
                2->{result.add(AlignedPhone(reference[a-1],null,"possible_omission"));a--}
                3->b--
                else->return PauseAlignmentResult("invalid_evidence")
            }}
            return PauseAlignmentResult("diagnostic_only",result.asReversed())
        } finally {
            maxima.fill(0);spans.forEach{it.mean.fill(0.0)}
            scratchCosts?.forEach{it.fill(0.0)};scratchActions?.forEach{it.fill(0)}
        }
    }
}

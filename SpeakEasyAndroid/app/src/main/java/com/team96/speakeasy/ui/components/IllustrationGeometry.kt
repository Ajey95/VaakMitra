package com.team96.speakeasy.ui.components

/** DEC061: one uniform scale keeps faces, hands and animals recognizable in every frame. */
data class IllustrationFrame(val scale:Float,val dx:Float,val dy:Float)
fun fitIllustration(width:Float,height:Float,artWidth:Float,artHeight:Float):IllustrationFrame {
    require(listOf(width,height,artWidth,artHeight).all{it.isFinite() && it>0f})
    val scale=minOf(width/artWidth,height/artHeight)
    require(scale.isFinite() && scale>0f)
    return IllustrationFrame(scale,((width-artWidth*scale)/2f).coerceAtLeast(0f),((height-artHeight*scale)/2f).coerceAtLeast(0f))
}

package com.team96.speakeasy.audio
/** DEC057: production peak capture or explicitly supplied public fake input; never retained audio. */
interface CandleInput {
 fun start():Boolean
 fun amplitude():Int
 val isRunning:Boolean
 fun cancel()
}

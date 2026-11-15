package com.team96.speakeasy.journey
/** DEC057 review R5: account data boundary, kept separate from pronunciation. */
fun confirmedAccountStars(total:Int?):Int?=total?.takeIf{it>=0}

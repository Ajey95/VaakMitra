package com.team96.speakeasy.journey

/** DEC053 review R6: absent authenticated identity is unavailable, never a shared account. */
fun verifiedLetterScope(account:String?,child:String,offlineReview:Boolean):String? {
    if(offlineReview)return letterProfileScope("Offline review",child)
    val identity=account?.trim()?.takeIf{it.isNotEmpty() && !it.equals("Offline review",true)} ?: return null
    return letterProfileScope(identity,child)
}

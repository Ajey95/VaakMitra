package com.team96.speakeasy.journey

import android.content.Context
import android.util.AtomicFile
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

/** DEC064: atomic disk state, without a failed SharedPreferences write's dirty process cache. */
class EncouragementStore(context:Context,private val owner:String?,private val currentOwner:()->String?){
 private val app=context.applicationContext
 private fun file():AtomicFile {
  val key=MessageDigest.getInstance("SHA-256").digest(checkNotNull(owner).toByteArray()).joinToString(""){"%02x".format(it)}
  return AtomicFile(File(app.filesDir,"praise-settings-v2/$key.txt"))
 }
 fun load():PraiseSettings {
  if(owner==null||owner!=currentOwner())return PraiseSettings()
  val atomic=file()
  if(atomic.baseFile.exists())return runCatching{
   val parts=atomic.openRead().bufferedReader().use{it.readText()}.trim().split('|')
   require(parts.size==4&&parts[0]=="2"&&parts[2] in listOf("0","1")&&parts[3] in listOf("0","1"))
   PraiseSettings(PraiseStyle.from(parts[1]),parts[2]=="1",parts[3]=="1")
  }.getOrDefault(PraiseSettings(automaticSpeech=false))
  return runCatching{val old=app.getSharedPreferences("vaakmitra_praise_v1",Context.MODE_PRIVATE)
   PraiseSettings(PraiseStyle.from(old.getString("${owner}_style",null)),old.getBoolean("${owner}_speech",true),old.getBoolean("${owner}_motion",true))
  }.getOrDefault(PraiseSettings(automaticSpeech=false))
 }
 fun save(value:PraiseSettings):Boolean {
  if(owner==null)return currentOwner()==null
  if(owner!=currentOwner())return false
  val atomic=file();var stream:FileOutputStream?=null
  val bytes="2|${value.style.wire}|${if(value.automaticSpeech)1 else 0}|${if(value.motion)1 else 0}\n".toByteArray()
  return try{
   stream=atomic.startWrite();stream.write(bytes);stream.fd.sync()
   if(owner!=currentOwner()){atomic.failWrite(stream);return false}
   atomic.finishWrite(stream);stream=null
   atomic.openRead().use{it.readBytes()}.contentEquals(bytes)
  }catch(_:Exception){stream?.let{atomic.failWrite(it)};false}
 }
}

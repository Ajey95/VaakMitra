package com.team96.speakeasy.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.Image
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.selection.toggleable
import androidx.compose.ui.semantics.Role
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.team96.speakeasy.audio.LocalTamilSpeaker
import com.team96.speakeasy.audio.SpeechReadiness
import com.team96.speakeasy.avatar.AvatarMotion
import com.team96.speakeasy.journey.*
import com.team96.speakeasy.viewmodel.AppViewModel
import com.team96.speakeasy.R
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import android.os.SystemClock

/** DEC062/PRS001..006: effort feedback has no scoring/star/unlock side effects. */
@Composable
fun EncouragementPanel(
 vm:AppViewModel,event:PraiseEvent,
 modifier:Modifier=Modifier,heading:String="Your effort stamp",eventKey:String="manual",
 automatic:Boolean=false,enabled:Boolean=true,settingsButton:Boolean=false,compact:Boolean=false,
 speak:((PraiseStyle,PraiseEvent)->Boolean)?=null,stop:()->Unit={},
 voiceStatus:(()->SpeechReadiness)?=null,
) {
 // DEC066/PRS009: block both the illustration and speaker setup at every legacy call site.
 if(automatic&&!automaticCelebrationEligible(event)){
  LaunchedEffect(vm,eventKey){vm.cancelPraise(eventKey)}
  return
 }
 BindPraiseBackground(vm)
 val context=LocalContext.current;val lifecycle=LocalLifecycleOwner.current.lifecycle
 val motionEnvironment=rememberAvatarMotionEnvironment()
 val identity=vm.wordIdentity();val owner=vm.praiseScope
 var settings by remember(identity){mutableStateOf(vm.loadPraiseSettings(context))}
 var status by remember(identity){mutableStateOf<String?>(null)}
 var dialog by rememberSaveable(identity){mutableStateOf(false)}
 var consumed by rememberSaveable(identity){mutableStateOf<String?>(null)}
 var resumed by remember(lifecycle){mutableStateOf(lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))}
 var manualOverride by remember(eventKey){mutableStateOf(false)}
 val scale=remember(identity){Animatable(1f)}
 val currentSpeak by rememberUpdatedState(speak);val currentStop by rememberUpdatedState(stop)
 val currentEnabled by rememberUpdatedState(enabled)
 val currentVoiceStatus by rememberUpdatedState(voiceStatus)
 val currentTicket by rememberUpdatedState(eventKey)
 val ownSpeaker=remember(context,identity,speak==null){
  if(vm.isPublicPreview||speak!=null)null else LocalTamilSpeaker(context,onUnavailable={status="Offline Tamil voice unavailable. Text and pictures still work."}){}
 }
 fun stopCheer(){currentStop();ownSpeaker?.stopPraise()}
 fun emit(value:PraiseSettings,auto:Boolean):Boolean {
  if(identity!=vm.wordIdentity()||owner!=vm.praiseScope||!currentEnabled||!lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED))return false
  if(auto && !vm.isPraiseCurrent(eventKey))return false
  if(vm.isPublicPreview){status=if(auto)"Public preview · automatic cheer" else "Public preview · no sound played";return true}
  val accepted=currentSpeak?.invoke(value.style,event) ?: ownSpeaker?.speakPraise(vm.praiseName,value.style,event)==true
  status=if(accepted)"Spoken encouragement" else "Offline Tamil voice unavailable. Text and pictures still work."
  return accepted
 }
 fun play(value:PraiseSettings=settings){
  manualOverride=true;vm.cancelPraise(eventKey);emit(value,false)
 }
 DisposableEffect(lifecycle,identity,ownSpeaker){
  val observer=LifecycleEventObserver{_,e->
   if(e==Lifecycle.Event.ON_PAUSE||e==Lifecycle.Event.ON_STOP){resumed=false;vm.cancelPraise(currentTicket);stopCheer()}
   if(e==Lifecycle.Event.ON_RESUME){resumed=true;if(owner==vm.praiseScope)settings=vm.loadPraiseSettings(context)}
  }
  lifecycle.addObserver(observer)
  onDispose{lifecycle.removeObserver(observer);stopCheer();ownSpeaker?.shutdown()}
 }
 LaunchedEffect(eventKey,resumed,enabled,manualOverride){
  if(!resumed){scale.snapTo(1f);return@LaunchedEffect}
  if(!enabled||manualOverride){vm.cancelPraise(eventKey);scale.snapTo(1f);return@LaunchedEffect}
  val claimed=if(automatic)vm.claimPraise(eventKey)else true
  val decision=consumePraise(consumed,eventKey,true,automatic&&settings.automaticSpeech&&!manualOverride,!enabled)
  val fresh=consumed!=decision.consumed;consumed=decision.consumed
  val motion=vm.guidePreference(context).motion
  if(fresh&&claimed&&settings.motion&&motion!=AvatarMotion.STILL&&motionEnvironment.foreground&&motionEnvironment.systemAnimations)launch{
   scale.snapTo(if(motion==AvatarMotion.REDUCED).98f else .92f)
   scale.animateTo(1f,tween(if(motion==AvatarMotion.REDUCED)400 else 800))
  }
  if(claimed&&decision.play){
   val started=SystemClock.elapsedRealtime()
   fun readiness()=currentVoiceStatus?.invoke()?:ownSpeaker?.readiness?:SpeechReadiness.UNAVAILABLE
   while(!vm.isPublicPreview && readiness()==SpeechReadiness.PREPARING && praiseWithinBudget(started,SystemClock.elapsedRealtime()) && vm.isPraiseCurrent(eventKey)&&resumed&&currentEnabled&&!manualOverride){delay(100)}
   if(vm.isPraiseCurrent(eventKey)&&resumed&&currentEnabled&&!manualOverride){
    if(praiseWithinBudget(started,SystemClock.elapsedRealtime()))emit(settings,true)
    else status="The cheer was skipped while the voice prepared. You can hear it again when ready."
   }
  }
 }
 Column(modifier.fillMaxWidth().background(HeritagePaper,RoundedCornerShape(14.dp)).border(1.dp,HeritageGold,RoundedCornerShape(14.dp)).padding(12.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
  Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(10.dp)){
   // DEC065/PRS008: reward art belongs to the existing card, never the selected guide.
   Image(
    painter=painterResource(R.drawable.vm_reward_veshti_man),
    contentDescription="Tamil reward companion in a veshti and cooling glasses",
    contentScale=ContentScale.Fit,
    modifier=Modifier.size(width=if(compact)48.dp else 88.dp,height=if(compact)72.dp else 132.dp).scale(if(settings.motion)scale.value else 1f),
   )
   Column(Modifier.weight(1f)){
    Text(heading,color=HeritageMaroon,fontWeight=FontWeight.Bold,fontSize=16.sp)
    Text("Cheer style: ${settings.style.title}",color=HeritageMuted,fontSize=12.sp)
   }
  }
  if(!compact)Text(praiseLine(vm.praiseName,settings.style,event),color=HeritageInk,fontSize=17.sp,lineHeight=25.sp)
  else Text(praiseName(vm.praiseName).ifBlank{"At your own pace"},color=HeritageInk,fontSize=13.sp)
  Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
   HeritageButton(if(automatic)"Hear again" else "Play sample",{play()},enabled=enabled&&resumed,secondary=automatic,modifier=Modifier.weight(1f))
   HeritageButton("Stop cheer",{manualOverride=true;vm.cancelPraise(eventKey);stopCheer();status="Cheer stopped"},secondary=true,modifier=Modifier.weight(1f))
  }
  status?.let{Text(it,color=HeritageMuted,fontSize=12.sp)}
  if(settingsButton)HeritageButton("Cheer settings",{stopCheer();dialog=true},secondary=true,modifier=Modifier.fillMaxWidth())
 }
 if(dialog){
  var draft by remember{mutableStateOf(settings)};var error by remember{mutableStateOf(false)}
  AlertDialog(onDismissRequest={stopCheer();dialog=false},containerColor=HeritagePaper,
   title={Text("A cheer that feels good",color=HeritageInk)},
   text={Column(Modifier.heightIn(max=420.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)){
    Text("Choose a style, try it, then save. The child's name stays on this device.",color=HeritageMuted)
    for(style in PraiseStyle.entries)HeritageButton(style.title,{draft=draft.copy(style=style)},secondary=draft.style!=style,modifier=Modifier.fillMaxWidth())
    Text(praiseLine(vm.praiseName,draft.style,PraiseEvent.PRACTICE),color=HeritageInk,fontSize=16.sp)
    Row(Modifier.fillMaxWidth().toggleable(draft.automaticSpeech,role=Role.Switch,onValueChange={draft=draft.copy(automaticSpeech=it)}),verticalAlignment=Alignment.CenterVertically){Text("Automatic spoken cheers",Modifier.weight(1f),color=HeritageInk);Switch(draft.automaticSpeech,null)}
    Row(Modifier.fillMaxWidth().toggleable(draft.motion,role=Role.Switch,onValueChange={draft=draft.copy(motion=it)}),verticalAlignment=Alignment.CenterVertically){Text("Celebration motion",Modifier.weight(1f),color=HeritageInk);Switch(draft.motion,null)}
    Text("Short effort cheers. Breaks and quiet are always welcome. Your guide's Still setting also keeps the stamp still.",color=HeritageMuted,fontSize=12.sp)
    HeritageButton("Preview this cheer",{play(draft)},modifier=Modifier.fillMaxWidth())
    HeritageButton("Stop cheer",{stopCheer()},secondary=true,modifier=Modifier.fillMaxWidth())
    status?.let{Text(it,color=HeritageMuted,fontSize=12.sp)}
    if(error)Text("These preferences could not be saved. Your previous choices are kept.",color=HeritageMaroon)
   }},
   confirmButton={TextButton(onClick={
    stopCheer()
    if(vm.savePraiseSettings(context,identity,draft)){settings=vm.loadPraiseSettings(context);dialog=false}else error=true
   }){Text("Save cheers",color=HeritageMaroon)}},
   dismissButton={TextButton(onClick={stopCheer();dialog=false}){Text("Cancel",color=HeritageMuted)}})
 }
}

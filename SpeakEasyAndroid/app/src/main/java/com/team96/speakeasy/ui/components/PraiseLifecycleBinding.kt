package com.team96.speakeasy.ui.components

import android.content.Context
import android.content.ContextWrapper
import androidx.activity.ComponentActivity
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.team96.speakeasy.viewmodel.AppViewModel

private fun activityLifecycle(context:Context):Lifecycle? {
 var current=context
 repeat(16){
  if(current is ComponentActivity)return (current as ComponentActivity).lifecycle
  val next=(current as? ContextWrapper)?.baseContext?:return null
  if(next===current)return null
  current=next
 }
 return null
}
/** Actual Activity background invalidates handoffs; navigation between its pages does not. */
@Composable fun BindPraiseBackground(vm:AppViewModel){
 val lifecycle=activityLifecycle(LocalContext.current)?:LocalLifecycleOwner.current.lifecycle
 DisposableEffect(lifecycle,vm){
  val observer=LifecycleEventObserver{_,event->if(event==Lifecycle.Event.ON_PAUSE||event==Lifecycle.Event.ON_STOP)vm.invalidatePraiseForBackground()}
  lifecycle.addObserver(observer);onDispose{lifecycle.removeObserver(observer)}
 }
}

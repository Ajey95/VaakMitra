package com.team96.speakeasy.ui.components
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
/** DEC057: existing actions, calm ink treatment; grows to fit enlarged text. */
@Composable fun BouncyButton(text:String,gradient:List<Color>,modifier:Modifier=Modifier,enabled:Boolean=true,leading:(@Composable ()->Unit)?=null,onClick:()->Unit){
 val shape=RoundedCornerShape(13.dp)
 Box(modifier.fillMaxWidth().heightIn(min=58.dp).clip(shape).background(if(enabled)HeritageMaroon else Color(0xFFE2D5BC)).border(1.5.dp,if(enabled)HeritageMaroon else HeritageMuted,shape).clickable(enabled=enabled,onClick=onClick).padding(horizontal=18.dp,vertical=15.dp),contentAlignment=Alignment.Center){
  Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.Center){leading?.invoke();Text(text,color=if(enabled)HeritagePaper else HeritageMuted,fontSize=18.sp,fontWeight=FontWeight.Bold,textAlign=TextAlign.Center)}
 }
}
@Composable fun GhostButton(text:String,modifier:Modifier=Modifier,onClick:()->Unit){
 HeritageButton(text,onClick,secondary=true,modifier=modifier.fillMaxWidth())
}
